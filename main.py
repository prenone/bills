import imaplib
import email
import os
import pymupdf 
import requests
from PIL import Image, ImageDraw
import schedule
import time

username = os.environ['PHYSCRAFT_IMAP_USER']
password = os.environ['PHYSCRAFT_IMAP_PASSWORD']
mail = imaplib.IMAP4_SSL("imap.gmail.com")

mail.login(username, password)
mail.select("inbox")

status, messages = mail.search(None, '(FROM "pebblehost@pebblehost.com" SUBJECT "Invoice Payment Confirmation")')
messages = messages[0].split()

attachments_dir = "attachments"
if not os.path.isdir(attachments_dir):
    os.mkdir(attachments_dir)


attachments_censored_dir = "attachments_censored"
if not os.path.isdir(attachments_censored_dir):
    os.mkdir(attachments_censored_dir)


sensitive_content = os.environ["PHYSCRAFT_BANNED_TEXT"].split(";")

for msg_num in messages:
    status, msg_data = mail.fetch(msg_num, "(RFC822)")
    
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_maintype() == "multipart" or part.get("Content-Disposition") is None:
                        continue
                    filename = part.get_filename()
                    if filename and filename.endswith(".pdf"):
                        filepath = os.path.join(attachments_dir, filename)
                        
                        with open(filepath, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        print(f"Saved attachment {filename} to {filepath}")

                        pdf_document = pymupdf.open(filepath)
                        
                        for page_num in range(len(pdf_document)):
                            page = pdf_document.load_page(page_num)
                            zoom = 5 # quality
                            mat = pymupdf.Matrix(zoom, zoom)
                            pix = page.get_pixmap(matrix=mat)
                            png_filename = os.path.join(attachments_dir, f"{filename}_page_{page_num}.png")
                            pix.save(png_filename)
                            img = Image.open(png_filename)
                            draw = ImageDraw.Draw(img)
                            
                            for word in sensitive_content:
                                text_instances = page.search_for(word)
                                for inst in text_instances:
                                    draw.rectangle([inst.x0 * zoom, inst.y0 * zoom, inst.x1 * zoom, inst.y1 * zoom], fill="black")
                            
                            redacted_png_filename = os.path.join(attachments_dir, f"{filename}_page_{page_num}_redacted.png")
                            img.save(redacted_png_filename)
                            print(f"Redacted sensitive content in {filename}_page_{page_num}")

                            img = Image.open(redacted_png_filename)
                            img = img.convert('RGB')
                            redacted_pdf_filename = os.path.join(attachments_censored_dir, filename)
                            img.save(redacted_pdf_filename)
                            print(f"Converted {redacted_png_filename} back to PDF")

                        pdf_document.close()


mail.logout()


def upload_file(filepath):
    url = os.environ["PHYSCRAFT_BILL_UPLOAD_URL"]

    headers = {"x-physcraft-admin-password": os.environ["PHYSCRAFT_ADMIN_PASSWORD"]}
    files = {"file": open(filepath, "rb")}
    response = requests.post(url, headers=headers, files=files)
    if response.status_code == 200:
        print(f"Successfully uploaded {filepath}")
    else:
        print(f"Failed to upload {filepath}: {response.text}")


def main_routine():
    for filename in os.listdir(attachments_censored_dir):
        if filename.endswith(".pdf"):
            filepath = os.path.join(attachments_censored_dir, filename)
            upload_file(filepath)

schedule.every(6).hours.do(main_routine)

main_routine()

while True:
    schedule.run_pending()
    time.sleep(30 * 60)