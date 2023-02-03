import os
from flask import Flask, send_file, request
from PIL import Image
import io
import json
from werkzeug.utils import secure_filename
from Crypto.Hash import SHA3_512
import time
from d2.lib.globals import env
import base64
from jose import jwe

# Initialize a Flask application
app = Flask(__name__)

# Define allowed image file extensions
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

# Define the path to the folder containing the original images
IMAGE_FOLDER = 'files'

# Define the path to the folder where the resized images will be cached
CACHE_FOLDER = 'cache'

# Define the path to the fallback image that will be returned if an error occurs
FALLBACK_IMAGE = '404.jpg'

# Define the breakpoints for non-square images
BREAKPOINTS = [320, 480, 768, 1024, 1280, 1600, 1920]

# Define the breakpoints for square images
SQUARE_BREAKPOINTS = [16, 32, 64, 128, 256, 512, 1024]

# Set Url (with slash)
SERVER_URL = '//127.0.0.1:5000/'

def allowed_file(filename):
    """
    Check if the file extension of the given filename is in the list of allowed extensions.

    :param filename: The name of the file
    :return: True if the file extension is allowed, False otherwise
    """
    return any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)


@app.route('/<path:filename>')
def resize_image(filename):
    """
    Resize an image based on its width and return the resized image. If the image has already been resized, it will be
    returned from the cache. If an error occurs, the fallback image will be returned with a 404 status code.

    :param filename: The name of the file to be resized
    :return: The resized image or the fallback image with a 404 status code
    """
    try:
        # Check if the width argument is provided in the URL
        if not request.args or not request.args.get('w'):
            raise Exception('Invalid width')

        # Get the requested width from the URL
        requested_width = int(request.args.get('w'))

        # Check if the requested width is valid
        if requested_width <= 0:
            raise Exception('Invalid width')

        # Check if the file type is allowed
        if not allowed_file(filename):
            raise Exception('Invalid file type')
        
        # Get the path to the original image
        file_path = os.path.join(IMAGE_FOLDER, filename)

        # Check if the original image exists
        if not os.path.isfile(file_path):
            raise Exception('not found')
        
        # Check if cached resized image exists
        cache_path = os.path.join(CACHE_FOLDER, f'{requested_width}_{filename}')
        if os.path.isfile(cache_path):
            # Open cached image
            with open(cache_path, 'rb') as f:
                # Read cached image into IO
                image_io = io.BytesIO(f.read())
                format = cache_path.split('.')[-1].lower()
                return send_file(image_io, mimetype=f'image/{format}')

        # Open original image
        with Image.open(file_path) as im:
            original_width, original_height = im.size
            aspect_ratio = original_width / original_height

            # Determine closest breakpoint based on aspect ratio
            if aspect_ratio == 1:
                if requested_width <= 15:
                    closest_breakpoint = 16
                else:
                    # Find the closest size to the given
                    closest_breakpoint = max([bp for bp in SQUARE_BREAKPOINTS if bp <= requested_width])
            else:
                if requested_width <= 319:
                    closest_breakpoint = 320
                else:
                    # Find the closest size to the given
                    closest_breakpoint = max([bp for bp in BREAKPOINTS if bp <= requested_width])
            
            # Change Filename incase "cloest_breakpoint" isnt valid (319/15 etc)
            cache_path = os.path.join(CACHE_FOLDER, f'{closest_breakpoint}_{filename}')

            # Set width and height
            width = closest_breakpoint
            height = int(width / aspect_ratio)

            # Make image into thumbnail
            im.thumbnail((width, height))
            
            # Set format
            format = im.format.lower()
            if format not in ['jpeg', 'png', 'gif', 'webp']:

                # The reason default to Webp as it has better compression and looking sharper.
                format = 'webp'
            
            # Set Io
            image_io = io.BytesIO()

            # Save image and seek to byte 0
            im.save(image_io, format,optimize=True)
            image_io.seek(0)

            # Store the resized image in cache
            with open(cache_path, 'wb') as f:
                f.write(image_io.getvalue())
            
            # Send file.
            return send_file(image_io, mimetype=f'image/{format}')
    except Exception as e:
        # Open 404 image and send
        # for the future, add logging of "not expected Exceptions" like real process errors, not just invalid params
        with open(FALLBACK_IMAGE, 'rb') as f:
            image_io = io.BytesIO(f.read())
            format = FALLBACK_IMAGE.split('.')[-1].lower()
            return send_file(image_io, mimetype=f'image/{format}'),404
@app.route('/',)
def index():

    # Open the fallback image and read its contents
    with open(FALLBACK_IMAGE, 'rb') as f:
        image_io = io.BytesIO(f.read())

        # Get the format of the image
        format = FALLBACK_IMAGE.split('.')[-1].lower()

         # Return the image file with a 404 status code
        return send_file(image_io, mimetype=f'image/{format}'),404
# Route for handling file uploads
@app.route('/upload',methods=['POST'])
def uploadFile():

    # Get the uploaded file from the request
    file = request.files.get('file',False)
    # Get the token from the request headers
    token = request.headers.get('Authorization',False)

    if token:
        # Decrypt the token
        dec_payload = jwe.decrypt(base64.urlsafe_b64decode(token), env['JWE'])
        if dec_payload and not app.debug == True:
            # Load the data from the decrypted payload or if in debug mode, skip
            data = json.loads(dec_payload.decode())

            # Check if the token has expired
            if data['expires_in'] <= round(time.time()):
                return '403',403

        if request.method == 'POST':
            # Get the file from the request
            file = request.files['file']

            # Check if the file is allowed
            if file and allowed_file(file.filename):

                # Create a SHA3-512 hash object
                h_obj = SHA3_512.new()

                # Get a secure filename for the file
                safe_name = secure_filename(file.filename)

                # Get the file extension
                ext = safe_name.split('.')[-1].lower()

                # Get the current timestamp
                timestamp = str(time.time()).encode()

                # Update the hash object with the filename and timestamp
                h_obj.update(safe_name.encode()+timestamp)

                # Generate a hosted name for the file using the hash object
                newFileName = h_obj.hexdigest()+'.'+ext

                # Generate the full path to the file using the new file name name
                filename = os.path.join(IMAGE_FOLDER, newFileName)

                # Save the uploaded file to the file system
                file.save(filename)

                # Open the saved image file using the PIL library
                with Image.open(filename) as im:

                    # Get the original width and height of the image
                    original_width, original_height = im.size

                    # Get the sizes of the breakpoints that are smaller than the original image width
                    sizes = [bp for bp in BREAKPOINTS if bp <= original_width]

                    # Create a source dictionary with the image link and available sizes
                    source = {
                        'link':SERVER_URL + secure_filename(newFileName),
                        'sizes':sizes
                    }

                    # Return the source dictionary as a JSON string
                    return json.dumps(source)

    # Return a 400 Bad Request response if the file upload fails
    # TODO: add better error codes (wrong file type, no auth etc)
    return '400',400
if __name__ == '__main__':
    # Start the Flask app in debug mode
    print('\033[93m Warning: Flask is set to debug mode, All token times are disabled. \033[0m \033[91m DO NOT USE IN PRODCTUON \033[0m')
    app.run(debug=True)
    
