from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.BankAPI
users = db["Users"]

def UserExist(username):
    return users.find({"Username":username}).count() != 0

def returnState(status, comments):
    return jsonify({
        "status": status,
        "msg": comments
    })

class Register(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        if UserExist(username):
            return returnState(301, "Invalid Username")

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # store username and password into database
        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Own": 0,
            "Debt": 0
        })

        return returnState(200, "You successfully signed up for the API")


def verifyPw(username, password):
    hashed_pw = users.find({
        "Username":username
    })[0]["Password"]

    return bcrypt.checkpw(password.encode('utf-8'), hashed_pw)


def countTokens(username):
    return users.find({
        "Username": username
    })[0]["Tokens"]


def verifyCredentials(username, password):
    if not UserExist(username):
        return returnState(301, "Invalid Username/Password"), True

    correct_pw = verifyPw(username, password)
    if not correct_pw:
        return returnState(302, "Invalid Username/Password"), True

    return None, False


def cashWithUser(username):
    return users.find({
        "Username":username
    })[0]["Own"]


def debtWithUser(username):
    return users.find({
        "Username":username
    })[0]["Debt"]

def updateAccount(username, balance):
    users.update({
        "Username": username
    }, {
        "$set": {
            "Own": balance
        }
    })

def updateDebt(username, balance):
    users.update({
        "Username": username
    }, {
        "$set": {
            "Debt": balance
        }
    })

class Add(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        amount = postedData["amount"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return retJson

        #Verify user store legal money
        if amount <= 0:
            return returnState(304, "The money amount entered must be greater than 0!")

        cash = cashWithUser(username)
        amount -= 1
        bank_cash = cashWithUser("BANK")
        updateAccount("BANK", bank_cash+1)
        updateAccount(username, cash+amount)

        return returnState(200, "Amount added successfully to account!")

class Withdraw(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        amount = postedData["amount"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return retJson

        #Verify user withdraw legal money
        if amount<=0:
            return returnState(304, "Illegal amount!")

        cash = cashWithUser(username)
        if amount > cash-1:
            return returnState(304, "Insufficient money!")

        bank_cash = cashWithUser("BANK")
        updateAccount("BANK", bank_cash+1)
        updateAccount(username, cash - amount - 1)

        return returnState(200, "Amount added successfully to account!")


class Transfer(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        receiver = postedData["receiver"]
        amount = postedData["amount"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return retJson

        if not UserExist(receiver):
            return returnState(301, "Receiver username is invalid")

        #Verify user want legal money
        if amount <= 0:
            return returnState(304, "The money amount entered must be greater than 0!")

        cash_from = cashWithUser(username)
        if cash_from<=0 or cash_from<amount+1:
            return returnState(304, "You're out of money, please add more or take a loan")

        cash_to = cashWithUser(receiver)
        bank_cash = cashWithUser("BANK")

        updateAccount("BANK", bank_cash+1)
        updateAccount(username, cash_from-amount-1)
        updateAccount(receiver, cash_to + amount)

        return returnState(200, "Amount Transfered successfully!")

class Balance(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        retJson, error = verifyCredentials(username, password)
        if error:
            return retJson

        retJson = users.find({
            "Username": username
        }, {
            "Password": 0,
            "_id": 0
        })[0]

        return jsonify(retJson)


class TakeLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        amount = postedData["amount"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return retJson

        if amount<=0:
            return returnState(304, "Illegal loan, must be greater than 0!")

        
        cash = cashWithUser(username)
        debt = debtWithUser(username)

        updateAccount(username, cash + amount)
        updateDebt(username, debt + amount)

        return returnState(200, "Loan added to your account!")

class PayLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        amount = postedData["amount"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return retJson
        
        if amount<=0:
            return returnState(304, "Illegal payment, must be greater than 0!")

        cash = cashWithUser(username)
        if cash<=0 and cash < amount:
            return returnState(303, "Not enough cash in your account")

        debt = debtWithUser(username)
        if debt<=0:
            return returnState(200, "You don't have any debt")


        updated_cash = cash - amount
        updated_debt = debt - amount
        if amount > debt:
            updated_cash = cash - debt
            updated_debt = 0        

        updateAccount(username, updated_cash)
        updateDebt(username, updated_debt)

        return returnState(200, "You've successfully paid your loan!")

api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Withdraw, '/withdraw')
api.add_resource(Transfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(TakeLoan, '/takeLoan')
api.add_resource(PayLoan, '/payLoan')

if __name__=="__main__":
    app.run(host='0.0.0.0')
