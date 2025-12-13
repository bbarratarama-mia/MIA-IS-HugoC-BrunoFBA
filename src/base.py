""" Base de datos y su interfaz """

import json 
import os
 
STATUS = "status" 
AMOUNT = "amount" 
PAYMENT_METHOD = "payment_method" 
 
STATUS_REGISTRADO = "REGISTRADO" 
STATUS_PAGADO = "PAGADO" 
STATUS_FALLIDO = "FALLIDO" 
 
DATA_PATH = "./persistent/data.json"  

def ensure_datafile():
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w") as f:
            json.dump({}, f)

def load_all_payments():
    ensure_datafile()
    with open(DATA_PATH, "r") as f: 
        data = json.load(f) 
    return data 
 
def save_all_payments(data):
    ensure_datafile()
    with open(DATA_PATH, "w") as f: 
        json.dump(data, f, indent=4) 
 
def load_payment(payment_id): 
    data = load_all_payments() 
    key = str(payment_id)
    if key not in data:
        raise KeyError(f'Pago {payment_id} no encontrado')
    return data[key]
 
def save_payment_data(payment_id, data): 
    all_data = load_all_payments() 
    all_data[str(payment_id)] = data 
    save_all_payments(all_data) 
 
def save_payment(payment_id, amount, payment_method, status): 
    data = { 
        AMOUNT: amount, 
        PAYMENT_METHOD: payment_method, 

        STATUS: status, 
    } 
    save_payment_data(payment_id, data) 

def payment_exists(payment_id) -> bool:
    data = load_all_payments()
    return str(payment_id) in data