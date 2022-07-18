from artshop import create_flask
from artshop.Blue_prints.requisites import *
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
from flask import Blueprint
from razorpay import Client
import os
import math
from flask import Flask, render_template, request, session, redirect, url_for, flash, abort
from flask_mail import Mail, Message
from random import randint, random
from datetime import datetime, timedelta
from functools import wraps
from itsdangerous import URLSafeSerializer
from werkzeug.utils import secure_filename


payment = Blueprint('payment', __name__, url_prefix='/buy')

app = create_flask()
db = MySQL(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
client = Client(auth=(os.getenv('RAZORPAY_KEY_ID'),
                      os.getenv('RAZORPAY_KEY_SECRET')))


@payment.route("/product/saveid_in_session", methods=["POST", "GET"])
@ user_login_required
def saveId():
    if request.method == "POST":
        pid = request.form["pid"]
        session["buying_product_id"] = pid
        cur = db.connection.cursor()
        try:
            res = cur.execute(
                "SELECT is_verified FROM users WHERE user_id=%s", (session['user_id'],))
        except:
            cur.close()
            abort(500)
        if res:
            is_verified = cur.fetchone()['is_verified']
            cur.close()
            if is_verified:
                return redirect(url_for("payment.chooseAddress"))
            else:
                flash('Verify your account to buy!', 'error')
                return redirect(url_for('user.product', id=pid))
        else:
            flash('Something went wrong! please try again later', 'error')
            return redirect(url_for('user.product', id=pid))
    else:
        abort(403)


@payment.route("/product/chooseaddress", methods=["POST", "GET"])
@ user_login_required
def chooseAddress():
    if not session["buying_product_id"] == "":
        cur = db.connection.cursor()
        try:
            result = cur.execute(
                "SELECT * FROM addresses WHERE user_id=(%s) ORDER BY address_id DESC", (session["user_id"],))
        except:
            cur.close()
            abort(500)
        if result:
            addresses = cur.fetchall()
        else:
            addresses = "no addresses"
        cur.close()
        return render_template("choose-address.html", addresses=addresses)
    else:
        flash("Please select product", "error")
        return redirect(url_for("user.yourWishlist", user=session["name"]))


@payment.route("/makepayment/newaddress/checkout", methods=["GET", "POST"])
@ user_login_required
def checkoutWithNewAddress():
    if request.method == "POST":
        fullName = request.form["full-name"]
        mobile = request.form["mobile-number"]
        pin = request.form["pin-number"]
        house = request.form["house"]
        area = request.form["area"]
        landmark = request.form["landmark"]
        town = request.form["town"]
        state = request.form["state"]
        address = house + " \n" + area + " \n" + landmark + " \n" + town + "\n" + state
        address_id = 'UAD_'+str(session['user_id']) + \
            str(math.ceil((random()*randint(0, 9))*10))
        cur = db.connection.cursor()
        try:
            cur.execute("INSERT INTO addresses (address_id,user_id,full_name,mobile,address) VALUES (%s,%s,%s,%s,%s)",
                        (address_id, session["user_id"], fullName, mobile, address))
            cur.connection.commit()
            flash("Address added, choose now", "success")
        except:
            flash("Something went wrong try again!", "error")
        cur.close()
        return redirect(url_for('payment.chooseAddress'))
    err = "Something went wrong!"
    return render_template("error.html", err=err)


@payment.route("/makepayment/checkout", methods=["GET", "POST"])
@ user_login_required
def checkout():
    if request.method == "POST":
        addressId = request.form["address-id"]
        cur = db.connection.cursor()
        try:
            result = cur.execute(
                "SELECT * FROM addresses WHERE address_id=(%s)", (addressId,))
        except:
            cur.close()
            abort(500)
        if result:
            address = cur.fetchone()
            try:
                preasult = cur.execute(
                    "SELECT * FROM products WHERE product_id=(%s)", (session["buying_product_id"],),)
            except:
                cur.close()
                abort(500)
            if preasult:
                product = cur.fetchone()
                tax_amt = int(product['price'])*.18
                price = int((product['price']+70+tax_amt)*100)
                create_order = {
                    "amount": price,
                    "currency": "INR",
                    "receipt": "recpt" + str(product["product_id"]),
                    "notes": address,
                    "payment_capture": "0",
                }
                # razorpay_resp = client.order.create(create_order)
                cur.close()
                return render_template("order.html", address=address, product=product, rprice=price)
            else:
                flash("Product doesn't exists anymore", "error")
                cur.close()
                return redirect(url_for("payment.checkout"))
        else:
            flash("Something went wrong", "error")
            cur.close()
            return redirect(url_for("payment.checkout"))
    abort(401)


@payment.route("/placeorder", methods=["GET", "POST"])
@ user_login_required
def placeOrder():
    if request.method == "POST":
        address_id = request.form["address-id"]
        cur = db.connection.cursor()
        try:
            cur.execute("SELECT * FROM products WHERE product_id =%s",
                        (session["buying_product_id"],))
            data = cur.fetchone()
            cur.execute("SELECT * FROM sellers WHERE seller_id=%s",
                        (data['seller_id'],))
            seller_data = cur.fetchone()
            seller_email = seller_data['seller_email']
            cur.execute(
                "SELECT * FROM addresses WHERE address_id=%s", (address_id,))
            uaddress = cur.fetchone()
        except:
            cur.close()
            abort(500)
        order_id = 'hcorder'+str(data['product_id']) + str(randint(100, 999))
        address = uaddress['full_name']+" \n" + \
            uaddress['address']+"\n" + "Ph: "+uaddress['mobile']
        try:
            result = cur.execute("INSERT INTO orders (order_id,product_id,seller,seller_id,address_id,user_id,product_name,product_img,product_type,address,user,ordered_on,price) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (
                order_id, data["product_id"], data["seller"], data['seller_id'], address_id, session["user_id"], data['product_name'], data['product_img'], data['product_type'], address, session['name'], getDateTime(), data["price"]))
            new_left_quantity = 0
            new_times_sold = data["times_sold"] + 1
            if data["product_quantity_left"] > 0:
                new_left_quantity = data["product_quantity_left"] - 1
            update_result = cur.execute("UPDATE products SET products.product_quantity_left=%s, products.times_sold=%s WHERE product_id=%s", (
                new_left_quantity, new_times_sold, session["buying_product_id"]),)
        except:
            cur.close()
            abort(500)
        if result and update_result:
            cur.connection.commit()
            # MAILING SECTION
            try:
                if cur.execute("SELECT * FROM orders WHERE order_id=%s", (order_id,)):
                    mail_data = cur.fetchone()
                    if cur.execute("SELECT * FROM users WHERE user_id=%s", (session['user_id'],)):
                        u_data = cur.fetchone()
                        if cur.execute("SELECT * FROM seller_details JOIN sellers ON sellers.seller_id=seller_details.seller_id WHERE seller_details.seller_id=%s", (mail_data['seller_id'],)):
                            seller_address = cur.fetchone()
                            seller_mail_msg = Message(
                                "New order alert!", sender="rur209@gmail.com", recipients=["rur209@gmail.com"])
                            user_mail_msg = Message(
                                "Your new order placed", sender="rur209@gmail.com", recipients=[u_data['email']])
                            mail_data['email'] = u_data['email']
                            mail_data['name'] = u_data['name']
                            seller_mail_msg.html = render_template(
                                'mails/seller-order-alert.html', mail_data=mail_data, brand='seller')
                            user_mail_msg.html = render_template(
                                'mails/user-order-mail.html', mail_data=mail_data, add=seller_address)
                            # try:
                            #     mail.send(seller_mail_msg)
                            #     mail.send(user_mail_msg)
                            # except:
                            #     pass
                            cur.close()
                            return redirect(url_for('user.yourOrders', user=session['name']))
            except:
                cur.close()
                abort(500)
            flash('Something went while sending order confirmation mail!', 'error')
            return redirect(url_for('user.yourOrders', user=session['name']))
        else:
            cur.close()
            abort(500)
    else:
        cur.close()
        abort(403)
