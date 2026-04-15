from tools.memory_manager import MemoryManager
import os

mm = MemoryManager()
res1 = mm.save_insight("曼联", "2024年4月发现：滕哈格在客场面对弱队时，由于中场控制力差，极易被打反击，大球概率高。", "match_123")
print("Save:", res1)

res2 = mm.retrieve_memory("曼联", "曼联客场防守表现如何？")
print("Retrieve:", res2)
