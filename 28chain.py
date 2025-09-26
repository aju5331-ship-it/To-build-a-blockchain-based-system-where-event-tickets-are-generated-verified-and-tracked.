import hashlib
import json
import time
import uuid
import sys
try:
    from ecdsa import SigningKey, VerifyingKey, NIST384p
except ModuleNotFoundError:
    raise ImportError(
        "The 'ecdsa' package is missing. Install it with:\n\n"
        "    pip install ecdsa flask\n"
    )

from flask import Flask, request, jsonify


class Transaction:
    def __init__(self, tx_type, data, sender_pubkey=None, signature=None):
        self.tx_type = tx_type
        self.data = data
        self.sender_pubkey = sender_pubkey
        self.signature = signature
        self.timestamp = time.time()

    def to_dict(self):
        return {
            "tx_type": self.tx_type,
            "data": self.data,
            "sender_pubkey": self.sender_pubkey,
            "signature": self.signature,
            "timestamp": self.timestamp
        }

    def compute_hash(self):
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()


class Block:
    def __init__(self, index, transactions, prev_hash, nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = time.time()
        self.prev_hash = prev_hash
        self.nonce = nonce

    def compute_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "transactions": [t.to_dict() for t in self.transactions],
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


class Blockchain:
    difficulty = 2

    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.create_genesis_block()
        self.tickets = {}

    def create_genesis_block(self):
        genesis_block = Block(0, [], "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    def add_transaction(self, transaction):
        self.pending_transactions.append(transaction)

    def mine(self):
        if not self.pending_transactions:
            return False
        new_block = Block(len(self.chain), self.pending_transactions, self.chain[-1].compute_hash())
        proof = self.proof_of_work(new_block)
        new_block.hash = proof
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block

    def proof_of_work(self, block):
        block.nonce = 0
        computed_hash = block.compute_hash()
        while not computed_hash.startswith("0" * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return computed_hash

    def verify_ticket(self, ticket_id):
        return self.tickets.get(ticket_id, None)

    def record_ticket(self, ticket_id, owner, status="valid"):
        self.tickets[ticket_id] = {"owner": owner, "status": status}


# ----- Flask API -----
app = Flask(__name__)
blockchain = Blockchain()


@app.route("/chain", methods=["GET"])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append({
            "index": block.index,
            "transactions": [t.to_dict() for t in block.transactions],
            "timestamp": block.timestamp,
            "prev_hash": block.prev_hash,
            "hash": block.compute_hash()
        })
    return jsonify(chain_data), 200


@app.route("/mine", methods=["POST"])
def mine():
    block = blockchain.mine()
    if not block:
        return jsonify({"message": "No transactions to mine"}), 200
    return jsonify({
        "index": block.index,
        "transactions": [t.to_dict() for t in block.transactions],
        "hash": block.hash
    }), 200


@app.route("/issue", methods=["POST"])
def issue_ticket():
    data = request.get_json()
    ticket_id = str(uuid.uuid4())
    tx = Transaction("issue", {
        "ticket_id": ticket_id,
        "event": data["event"],
        "owner": data["owner"],
        "price": data["price"]
    }, sender_pubkey=data.get("issuer_pubkey"), signature=data.get("issuer_signature"))
    blockchain.add_transaction(tx)
    blockchain.record_ticket(ticket_id, data["owner"])
    return jsonify({"message": "Ticket issued", "ticket_id": ticket_id}), 201


@app.route("/transfer", methods=["POST"])
def transfer_ticket():
    data = request.get_json()
    ticket = blockchain.verify_ticket(data["ticket_id"])
    if not ticket or ticket["status"] != "valid":
        return jsonify({"error": "Invalid ticket"}), 400
    tx = Transaction("transfer", {
        "ticket_id": data["ticket_id"],
        "new_owner": data["new_owner"]
    }, sender_pubkey=data.get("sender_pubkey"), signature=data.get("signature"))
    blockchain.add_transaction(tx)
    blockchain.record_ticket(data["ticket_id"], data["new_owner"])
    return jsonify({"message": "Ticket transferred"}), 200


@app.route("/redeem", methods=["POST"])
def redeem_ticket():
    data = request.get_json()
    ticket = blockchain.verify_ticket(data["ticket_id"])
    if not ticket or ticket["status"] != "valid":
        return jsonify({"error": "Invalid or already redeemed ticket"}), 400
    tx = Transaction("redeem", {
        "ticket_id": data["ticket_id"]
    }, sender_pubkey=data.get("sender_pubkey"), signature=data.get("signature"))
    blockchain.add_transaction(tx)
    blockchain.record_ticket(data["ticket_id"], ticket["owner"], status="redeemed")
    return jsonify({"message": "Ticket redeemed"}), 200


@app.route("/ticket/<ticket_id>", methods=["GET"])
def ticket_history(ticket_id):
    history = []
    for block in blockchain.chain:
        for t in block.transactions:
            if t.data.get("ticket_id") == ticket_id:
                history.append(t.to_dict())
    return jsonify(history), 200


@app.route("/verify/<ticket_id>", methods=["GET"])
def verify(ticket_id):
    ticket = blockchain.verify_ticket(ticket_id)
    if not ticket:
        return jsonify({"valid": False, "message": "Ticket not found"}), 404
    return jsonify({"valid": ticket["status"] == "valid", "ticket": ticket}), 200


# Key utilities
def generate_keys():
    sk = SigningKey.generate(curve=NIST384p)
    vk = sk.verifying_key
    print("Private key:", sk.to_string().hex())
    print("Public key:", vk.to_string().hex())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "genkeys":
        generate_keys()
    else:
        app.run(debug=True)
