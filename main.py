from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.background import BackgroundTasks
from redis_om import get_redis_connection, HashModel
from starlette.requests import Request
import time, requests

app = FastAPI()

# it should be a different database
# since I am using free version this is fine
# This could be a No SQL or Mongo DB database
redis = get_redis_connection(
    host="redis_hostname",
    port = redis_port,
    password = "password",
    decode_responses = True
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins = ['http://localhost:3000'],
    allow_methods = ['*'],
    allow_headers = ['*']
)

class Order(HashModel):
    product_id: str
    price: float
    # fee is as such fee of warehouse from where you are buying the product from
    fee: float
    # total = fee + price
    total: float
    quantity: int
    # status = pending, completed, refunded (when any error occurs)
    status: str 

    class Meta:
        database = redis
@app.get('/orders/{pk}')
def get(pk: str):
    return Order.get(pk)

@app.post('/orders')
async def create(request: Request, background_tasks: BackgroundTasks): # Here we will send id and quantity of Orders
    body = await request.json()
    
    # requesting data from inventory microservice
    req = requests.get('http://localhost:8000/products/%s' % body['id'])

    product = req.json()
    order = Order(
        product_id = body['id'], # get id from body as we are the one's sending it
        price = product['price'],
        fee = 0.2*product['price'],
        total = 1.2*product['price'],
        quantity = body['quantity'], # get id from body as we are the one's sending it
        status = 'pending' # awaiting for payment processor to finish the order
    )
    order.save()

    # call background task function pass the parameter required
    background_tasks.add_task(order_completed, order)

    return order

def order_completed(order: Order):
    # sleeping until the payment is process is completed
    time.sleep(10)
    order.status = 'completed'
    order.save()
    # when the order is completed we will change the satus to completed
    # and we will send the events to redis
    redis.xadd('order_completed', order.dict(), '*')
    
