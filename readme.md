## Sloth CDN implements a Flask-based REST API for resizing images.
It uses the Flask library to create a web server that listens to incoming requests, and the PIL library to resize images. The API allows clients to request a resized version of an image by specifying the desired width in the URL.

The API checks if a resized version of the requested image already exists in the cache folder. If it does, the cached version is returned. If not, the original image is loaded and resized to the closest breakpoint based on the aspect ratio of the image. The resized image is then saved to the cache folder for future requests.

The API implements basic security measures, such as checking if the file type is allowed and validating the width argument in the URL. Additionally, it uses the SHA3_512 hash function from the Crypto library to hash filenames for security purposes, and the jose library to encrypt the images using JWE encryption. Overall, this code provides a simple and efficient solution for resizing images through a REST API. The code can be named as 

<hr>
how to make a token:

```python
import json
import time
import base64
from jose import jwe
env = 'something that is compliant with A256GCM' #you need to also add ENV to server.py
def createRmoteToken():
        """
        Returns a JSON Web token (JWT) that is allowed for auth (JWE)
        
        Encryption is A256GCM.
        """
        try:
            # you can put whatever you wish in here.
            payload = {
                "expires_in": round(time.time()) + 120, #2 minutes expire time
            }
            print('expires at'+str(payload['expires_in']))
            enc_payload = base64.urlsafe_b64encode(jwe.encrypt(json.dumps(payload), env, algorithm='dir', encryption='A256GCM'))
            return enc_payload
        except Exception as e:
            return False
```
<!-- the name is because i like Sloths... oh well -->
