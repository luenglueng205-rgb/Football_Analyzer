import os
import sys
import json
import logging
import asyncio
from typing import List, Dict, Any
from tqdm import tqdm
import time
import argparse
from standalone_workspace.tools.paths import data_dir, HISTORICAL_DATA_FILENAME, datasets_dir

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from standalone_workspace.tools.memory_manager import MemoryManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 定义断点续传的游标文件
CHECKPOINT_FILE = os.path.join(data_dir(), "ingestion_checkpoint.json")

def load_checkpoint() -> int:
    """加载断点续传的游标（已处理的记录数）"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("processed_count", 0)
        except Exception as e:
            logger.warning(f"无法读取断点文件: {e}")
    return 0

def save_checkpoint(processed_count: int):
    """保存断点续传的游标"""
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({"processed_count": processed_count, "last_updated": time.time()}, f)

def _translate_score_to_tags(home_goals: int, away_goals: int, handicap: int = -1) -> List[str]:
    """将真实比分降维翻译为体彩专属标签"""
    tags = []
    
    # 1. 竞彩胜平负
    if home_goals > away_goals:
        tags.append("[JC_HomeWin]")
    elif home_goals == away_goals:
        tags.append("[JC_Draw]")
    else:
        tags.append("[JC_AwayWin]")
        
    # 2. 竞彩让球 (默认主让1球)
    handicap_diff = home_goals + handicap - away_goals
    if handicap_diff > 0:
        tags.append(f"[JC_Handicap_{handicap}_HomeWin]")
    elif handicap_diff == 0:
        tags.append(f"[JC_Handicap_{handicap}_Draw]")
    else:
        tags.append(f"[JC_Handicap_{handicap}_AwayWin]")
        
    # 3. 竞彩总进球
    total_goals = home_goals + away_goals
    tags.append(f"[JC_Total_{total_goals}]")
    if total_goals >= 3:
        tags.append("[JC_Over_2.5]")
    else:
        tags.append("[JC_Under_2.5]")
        
    # 4. 北单上下单双
    shang_xia = "上盘" if total_goals >= 3 else "下盘"
    dan_shuang = "单" if total_goals % 2 != 0 else "双"
    tags.append(f"[BD_{shang_xia}{dan_shuang}]")
    
    return tags

async def ingest_historical_data(batch_size: int = 500):
    """
    Ingest the massive 220k match dataset into ChromaDB as episodic memory with resume support.
    """
    data_path = os.path.join(datasets_dir("raw"), HISTORICAL_DATA_FILENAME)
    if not os.path.exists(data_path):
        logger.error(f"Data file not found at {data_path}")
        return

    logger.info("Loading JSON dataset into memory (this may take a moment)...")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    matches = data.get("matches", [])
    total_matches = len(matches)
    logger.info(f"Loaded {total_matches} matches from JSON.")
    
    memory_manager = MemoryManager()
    
    start_index = load_checkpoint()
    if start_index >= total_matches:
        logger.info("所有数据已注入完毕！如果要重新注入，请删除 data_dir() 下的 ingestion_checkpoint.json")
        return
        
    logger.info(f"断点续传启动：将从第 {start_index} 条记录开始注入，剩余 {total_matches - start_index} 条。")
    logger.info(f"Batch size: {batch_size}")
    
    # 从断点处继续
    target_matches = matches[start_index:]
    processed_in_this_run = 0
    
    try:
        for i in tqdm(range(0, len(target_matches), batch_size), desc="Ingesting batches"):
            batch = target_matches[i:i+batch_size]
            
            memories = []
            for match in batch:
                # Create a rich semantic text string for the vector search
                home_g = int(match.get('home_goals', 0))
                away_g = int(match.get('away_goals', 0))
                lottery_tags = _translate_score_to_tags(home_g, away_g)

                text_content = (
                    f"League: {match.get('league')} | Date: {match.get('date')} | "
                    f"Match: {match.get('home_team')} vs {match.get('away_team')} | "
                    f"Result: {match.get('result')} ({home_g} - {away_g}) | "
                    f"Odds: Home {match.get('home_odds')}, Draw {match.get('draw_odds')}, Away {match.get('away_odds')} | "
                    f"Lottery Tags: {' '.join(lottery_tags)}"
                )
                
                metadata = {
                    "league": str(match.get("league")),
                    "date": str(match.get("date")),
                    "home_team": str(match.get("home_team")),
                    "away_team": str(match.get("away_team")),
                    "result": str(match.get("result")),
                    "home_odds": float(match.get("home_odds", 0.0) or 0.0),
                    "draw_odds": float(match.get("draw_odds", 0.0) or 0.0),
                    "away_odds": float(match.get("away_odds", 0.0) or 0.0),
                    "type": "historical_match"
                }
                
                # Use a unique ID based on date and teams
                match_id = f"{match.get('date')}_{match.get('home_team')}_{match.get('away_team')}".replace(" ", "_")
                
                memories.append({
                    "id": match_id,
                    "text": text_content,
                    "metadata": metadata,
                    "lottery_tags": lottery_tags
                })
                
            # Bulk add to ChromaDB episodic collection
            try:
                for m in memories:
                    memory_manager.add_episodic_memory(
                        content=m["text"],
                        tags=["historical", m["metadata"]["league"], m["metadata"]["home_team"], m["metadata"]["away_team"]] + m["lottery_tags"],
                        importance=0.8
                    )
                
                processed_in_this_run += len(batch)
                save_checkpoint(start_index + processed_in_this_run)
                
                # 防封禁与内存缓冲：每跑完一个 batch 稍微休息一下
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error inserting batch at index {start_index + processed_in_this_run}: {e}")
                # 遇到错误时也保存游标，避免下次重跑
                save_checkpoint(start_index + processed_in_this_run)
                raise e # 抛出异常以安全退出
                
        logger.info(f"Data ingestion completed successfully! Total processed: {start_index + processed_in_this_run}")
        
    except KeyboardInterrupt:
        logger.info(f"\nUser interrupted. Checkpoint saved at {start_index + processed_in_this_run}.")
    except Exception as e:
        logger.error(f"\nProcess stopped due to error. Checkpoint saved at {start_index + processed_in_this_run}. Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest massive historical match data into ChromaDB.")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for embedding ingestion")
    args = parser.parse_args()
    
    asyncio.run(ingest_historical_data(batch_size=args.batch_size))
