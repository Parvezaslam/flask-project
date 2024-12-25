from itsdangerous import URLSafeTimedSerializer   
from key import salt
def encode(data):
    serailizer= URLSafeTimedSerializer('code@123')  
    return serailizer.dumps(data,salt=salt)    
def decode(data):
    serailizer= URLSafeTimedSerializer('code@123') 
    return serailizer.loads(data,salt=salt)          