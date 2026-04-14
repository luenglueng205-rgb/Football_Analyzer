import os
import qrcode

def generate_ticket_qr(ticket_string: str, output_path: str = "tickets/latest_ticket.png") -> dict:
    """Generates a QR code for a betting ticket string."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(ticket_string)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)
        
        return {
            "status": "success",
            "file_path": output_path,
            "ticket_string": ticket_string
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
