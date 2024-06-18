from flask import Flask, render_template, request, redirect, send_file, flash,url_for
from werkzeug.utils import secure_filename
from PIL import Image
import os
import numpy as np

# Initialize Flask application
app = Flask(__name__)
app.secret_key = 'super_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'png'}

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

FIXED_KEY = 42  # Replace with your desired fixed key

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def encrypt_decrypt_message(message, key):
    encrypted_decrypted_chars = []
    for char in message:
        encrypted_decrypted_char = chr(ord(char) ^ key)
        encrypted_decrypted_chars.append(encrypted_decrypted_char)
    encrypted_decrypted_message = ''.join(encrypted_decrypted_chars)
    return encrypted_decrypted_message

def encrypt_pixels(img, key):
    np.random.seed(key)
    img_array = np.array(img)
    flattened = img_array.flatten()
    np.random.shuffle(flattened)
    encryptd_array = flattened.reshape(img_array.shape)
    encryptd_img = Image.fromarray(encryptd_array.astype('uint8'), mode=img.mode)
    return encryptd_img

def decrypt_pixels(img, key):
    np.random.seed(key)
    img_array = np.array(img)
    flattened = img_array.flatten()
    indices = np.arange(flattened.shape[0])
    np.random.shuffle(indices)
    inverse_indices = np.argsort(indices)
    unflattened = flattened[inverse_indices]
    decryptd_array = unflattened.reshape(img_array.shape)
    decryptd_img = Image.fromarray(decryptd_array.astype('uint8'), mode=img.mode)
    return decryptd_img

def encode_image(img, message):
    encoded_img = img.copy()
    encrypted_message = encrypt_decrypt_message(message, FIXED_KEY)
    encrypted_message += "###"  # End-of-message indicator
    binary_message = ''.join(format(ord(char), '08b') for char in encrypted_message)
    index = 0

    for x in range(img.size[0]):
        for y in range(img.size[1]):
            pixel = list(img.getpixel((x, y)))
            for n in range(3):  # Only modify the first three values (RGB)
                if index < len(binary_message):
                    pixel[n] = (pixel[n] & ~1) | int(binary_message[index])
                    index += 1
                else:
                    encoded_img.putpixel((x, y), tuple(pixel))
                    return encrypt_pixels(encoded_img, FIXED_KEY)  # encrypt pixels after encoding
            encoded_img.putpixel((x, y), tuple(pixel))
    return encrypt_pixels(encoded_img, FIXED_KEY)  # encrypt pixels after encoding

def decode_image(img):
    decryptd_img = decrypt_pixels(img, FIXED_KEY)  # decrypt pixels before decoding
    binary_data = ""
    encrypted_message = ""
    
    for x in range(decryptd_img.size[0]):
        for y in range(decryptd_img.size[1]):
            pixel = decryptd_img.getpixel((x, y))
            for n in range(3):
                binary_data += str(pixel[n] & 1)
                if len(binary_data) == 8:
                    character = chr(int(binary_data, 2))
                    binary_data = ""
                    if encrypted_message.endswith("###"):  # Check for end-of-message indicator
                        decrypted_message = encrypt_decrypt_message(encrypted_message[:-3], FIXED_KEY)
                        return decrypted_message  # Return message without the indicator
                    encrypted_message += character
    if encrypted_message.endswith("###"):
        decrypted_message = encrypt_decrypt_message(encrypted_message[:-3], FIXED_KEY)
        return decrypted_message
    return ""

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/encode', methods=['GET', 'POST'])
def encode():
    if request.method == 'POST':
        file = request.files.get('file')
        message = request.form.get('message')
        if not file or not message:
            flash('Missing file or message')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            img = Image.open(file.stream)
            # Use the FIXED_KEY for encryption
            encoded_img = encode_image(img, message)
            encoded_img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"encoded_{filename}")
            encoded_img.save(encoded_img_path)
            return send_file(encoded_img_path, as_attachment=True)
    return render_template('encode.html')

@app.route('/decode', methods=['GET', 'POST'])
def decode():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('Missing file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            img = Image.open(file.stream)

            # Decode the message and decrypt the image using the FIXED_KEY
            decoded_message = decode_image(img)
            decryptd_img = decrypt_pixels(img, FIXED_KEY)  # decrypt image for visual display

            # Save the decryptd image
            decryptd_img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"decryptd_{filename}")
            decryptd_img.save(decryptd_img_path)

            # Provide a link to download the decryptd image and show the decoded message
            # file_url = f"{request.url_root}{os.path.join('uploads', 'decryptd_' + filename)}"
            file_url = url_for('static', filename='uploads/' + 'decryptd_' + filename) 
            return render_template('decoded.html', message=decoded_message, file_url=file_url)
    return render_template('decode.html')


if __name__ == '__main__':
    app.run(debug=True)
