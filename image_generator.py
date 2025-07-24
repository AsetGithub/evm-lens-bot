from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
import logging

# Konfigurasi gambar
IMG_WIDTH = 800
IMG_HEIGHT = 450
FONT_FILE = "PermanentMarker-Regular.ttf"

def create_transaction_image(tx_data):
    """
    Membuat gambar kuitansi transaksi dari data yang diberikan.
    """
    try:
        logging.info("Mencoba membuat gambar kuitansi...")
        # Siapkan font
        font_title = ImageFont.truetype(FONT_FILE, size=32)
        font_main = ImageFont.truetype(FONT_FILE, size=24)
        font_small = ImageFont.truetype(FONT_FILE, size=18)
        logging.info(f"Font '{FONT_FILE}' berhasil dimuat.")

        # Buat kanvas gambar
        image = Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT), color='#1E1E2E')
        draw = ImageDraw.Draw(image)

        # --- Gambar Konten ---
        draw.text((40, 30), "Transaction Receipt", fill='#F5C2E7', font=font_title)
        draw.line([(40, 75), (IMG_WIDTH - 40, 75)], fill='#45475A', width=2)

        y_pos = 100
        draw.text((40, y_pos), "Chain:", fill='#A6ADC8', font=font_main)
        draw.text((180, y_pos), tx_data['chain'].title(), fill='#F9E2AF', font=font_main)

        y_pos += 40
        draw.text((40, y_pos), "Status:", fill='#A6ADC8', font=font_main)
        draw.text((180, y_pos), tx_data['direction'], fill=tx_data['color'], font=font_main)
        
        y_pos += 40
        draw.text((40, y_pos), "Amount:", fill='#A6ADC8', font=font_main)
        draw.text((180, y_pos), tx_data['amount_text'], fill='#FFFFFF', font=font_main)

        y_pos += 40
        draw.text((40, y_pos), "From:", fill='#A6ADC8', font=font_main)
        draw.text((180, y_pos), tx_data['from_addr'], fill='#89B4FA', font=font_small)
        
        y_pos += 30
        draw.text((40, y_pos), "To:", fill='#A6ADC8', font=font_main)
        draw.text((180, y_pos), tx_data['to_addr'], fill='#89B4FA', font=font_small)

        # QR Code
        tx_url = f"{tx_data['explorer_url']}/tx/{tx_data['tx_hash']}"
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(tx_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        image.paste(qr_img, (IMG_WIDTH - 190, 100))
        draw.text((IMG_WIDTH - 188, 255), "Scan for Details", fill='#A6ADC8', font=font_small)

        # --- Simpan ke Memori ---
        image_buffer = io.BytesIO()
        image.save(image_buffer, format='PNG')
        image_buffer.seek(0)
        
        logging.info("Gambar kuitansi berhasil dibuat dan disimpan ke buffer.")
        return image_buffer

    except FileNotFoundError:
        logging.error(f"FATAL: File font '{FONT_FILE}' tidak ditemukan! Pastikan file ada di repositori.")
        return None
    except Exception as e:
        logging.error(f"Gagal membuat gambar: {e}")
        return None