import random
import string

def randomTransactionId():
    def generate_random_string(length):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for i in range(length))

    x_client_transaction_id = f"{generate_random_string(19)}/{generate_random_string(3)}/{generate_random_string(18)}+{generate_random_string(51)}"
    return x_client_transaction_id

print(randomTransactionId())