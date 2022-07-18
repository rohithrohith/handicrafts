from artshop import create_flask
from artshop.Blue_prints.requisites import *
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
from flask import Blueprint
import os
import math
import base64
import shutil
from flask import Flask, render_template, request, session, redirect, url_for, flash, abort
from random import randint, random
from datetime import datetime, timedelta
from functools import wraps
from itsdangerous import URLSafeSerializer
from werkzeug.utils import secure_filename


user = Blueprint('user', __name__, template_folder='user_templates')


app = create_flask()
db = MySQL(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
s = URLSafeSerializer(app.config["SECRET_KEY"])


@user.route("/")
@user.route("/home")
def home():
    cur = db.connection.cursor()
    try:
        result = cur.execute(
            "SELECT * FROM products WHERE product_quantity_left != 0 ORDER BY  rating DESC,times_sold DESC LIMIT 6")
    except:
        cur.close()
        abort(500)
    if result:
        products = cur.fetchall()
    else:
        flash("Sorry, no products in 'Handicrafts' database!", 'error')
        products = 'no data'
    cur.close()
    return render_template("home.html", products=products)


@user.route("/about")
def about():
    return render_template('about.html')


@user.route("/signin", methods=["POST", "GET"])
def signin():
    try:
        if session['logged_in']:
            flash('Already logged in!', 'success')
            return redirect(url_for('user.home'))
    except:
        pass
    if request.method == "POST":
        signin_mail = request.form["signin-email"]
        signin_password = request.form["signin-password"]
        cur = db.connection.cursor()
        try:
            res = cur.execute(
                "SELECT * FROM users WHERE email=(%s)", (signin_mail,))
        except:
            cur.close()
            abort(500)
        if res:
            data = cur.fetchone()
            dbpassword = data["password"]
            if not bcrypt.check_password_hash(dbpassword, signin_password):
                flash('Incorrect password', 'error')
            else:
                session["logged_in"] = True
                session["buying_product_id"] = ""
                session["mail"] = data["email"]
                session["name"] = data["name"]
                session["user_id"] = data["user_id"]
                flash("Successfully logged in", "success")
                return redirect(url_for('user.home'))
        else:
            flash("User does not exist, try signing up", 'error')
        cur.close()
    return render_template("signin.html")


@user.route("/register", methods=["POST", "GET"])
def register():
    error = ""
    if request.method == "POST":
        reg_name = request.form["signup-name"]
        reg_email = request.form["signup-email"]
        reg_password = request.form["signup-password"]
        reg_cpassword = request.form["signup-confirm-password"]
        if not reg_password == reg_cpassword:
            error = "Passwords doesn't match"
        else:
            cur = db.connection.cursor()
            try:
                res = cur.execute(
                    "SELECT * FROM users WHERE email=(%s)", (reg_email,))
            except:
                cur.close()
                abort(500)
            if res:
                error = "User already exist, try signing in"
            else:
                try:
                    insert_res = cur.execute("INSERT INTO users (name,email,password) VALUES (%s,%s,%s)", (
                        reg_name, reg_email, bcrypt.generate_password_hash(reg_password).decode("utf-8")))
                except:
                    cur.close()
                    abort(500)
                if insert_res:
                    cur.connection.commit()
                    try:
                        uid_result = cur.execute(
                            "SELECT user_id FROM users WHERE email=%s", (
                                reg_email,)
                        )
                    except:
                        cur.close()
                        abort(500)
                    if uid_result:
                        user_id = cur.fetchone()["user_id"]
                        token = s.dumps(reg_email, salt="email-verify")
                        mail_msg = Message(
                            "Hello %s! Verify your E-mail" % (reg_name),
                            sender="rur209@gmail.com",
                            recipients=[reg_email],
                        )
                        action = 'localhost:9000/user/%s/email/verification/%s' % (
                            user_id, token)
                        mail_msg.html = render_template(
                            '/mails/account-verify.html', action=action, brand='buyer', user=reg_name)

                        try:
                            # mail.send(mail_msg)

                            flash(
                                "Verification link is sent to your E-mail, verify your account before two minutes",
                                "success",
                            )
                        except:
                            flash(
                                'Registration successful, Verify your account in "Your account" section', 'success')
                        cur.close()
                        return redirect(url_for('user.signin'))
                    else:
                        error = 'Sorry something went wrong! try again'
                else:
                    error = "Something went wrong! please try again"
            cur.close()
        flash(error, "error")
    return render_template("register.html")


@user.route("/user/<string:id>/email/verification/<string:token>")
def verifyUserEmail(id, token):
    try:
        email = s.loads(token, salt="email-verify")
    except:
        err = "Link expired!"
        return render_template("error.html", err=err)
    cur = db.connection.cursor()
    data = getUserById(id, url_for('user.signin'))
    is_verified = data["is_verified"]
    dbemail = data["email"]
    if is_verified:
        err = "Account is already verified!"
        cur.close()
        return render_template("error.html", err=err)
    else:
        try:
            result = cur.execute(
                "UPDATE `users` SET `is_verified` = '1' WHERE `users`.`user_id` = %s", (
                    id,)
            )
        except:
            cur.close()
            abort(500)
        if result:
            cur.connection.commit()
            flash("Account verified", "success")
            cur.close()
            return redirect(url_for("user.signin"))
        else:
            cur.close()
            abort(500)


@user.route("/external/emailverification/<string:email>")
@user_login_required
def externalUserEmailVerify(email):
    token = s.dumps(email, salt="email-verify")
    subject = "Hello %s! Verify your E-mail" % (session["name"],)
    mail_msg = Message(
        subject,
        sender="rur209@gmail.com",
        recipients=[email],
    )
    mail_msg.html = render_template(
        '/mails/account-verify.hmtl', token=token, user=session['name'])
    try:
        mail.send(mail_msg)
        flash("Check your E-mail for verification link", "success")
    except:
        flash("Something went wrong! please try again later")
    return redirect(url_for("user.userAccount", user=session["name"]))


@user.route("/<string:user>/changepassword", methods=["POST", "GET"])
@user_login_required
def changePassword(user):
    if request.method == "POST":
        cur_password = request.form["current-password"]
        new_password = request.form["new-password"]
        confirm_new_password = request.form["confirm-new-password"]
        cur = db.connection.cursor()
        data = getUserById(session['user_id'], url_for(
            'user.changePassword', user=session['name']))
        dbpassword = data["password"]
        if not bcrypt.check_password_hash(dbpassword, cur_password):
            flash("Incorrect current password", "error")
        else:
            if not new_password == confirm_new_password:
                flash("New passwords doesn't match", "error")
            else:
                try:
                    ures = cur.execute(
                        "UPDATE users set password=(%s) WHERE user_id=(%s)",
                        (
                            bcrypt.generate_password_hash(new_password),
                            session["user_id"],
                        ),
                    )
                except:
                    cur.close()
                    abort(500)
                cur.connection.commit()
                cur.close()
                flash("Password changed", "success")
                return redirect(url_for("user.signin"))
        cur.close()
    return render_template("change-password.html")


@user.route("/forgotpassword", methods=["GET", "POST"])
def forgotPassword():
    if request.method == "POST":
        email = request.form["forgot-email"]
        cur = db.connection.cursor()
        try:
            res = cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        except:
            cur.close()
            abort(500)
        if res:
            otp = generateOTP()
            print(otp)
            now = datetime.now()
            session["hc_user_otp_expiring_time"] = now + timedelta(minutes=10)
            session['hc_user_email'] = email
            session["hc_user_reset_otp"] = otp
            mail_msg = Message(
                "OTP for Password reset",
                sender="rur209@gmail.com",
                recipients=[email]
            )
            mail_msg.html = render_template(
                'mails/forgot-password.html', otp=otp)
            # try:
            #     mail.send(mail_msg)
            #     flash('OPT sent', 'success')
            # except:
            #     flash('Error occured while sending OTP please try agin later', 'error')
            #     cur.close()
            #     return redirect(url_for('user.forgotPassword'))
            cur.close()
            return render_template("reset-otp.html")
        else:
            flash('Account, with given E-mail address does not exist', 'error')
        cur.close()
        return redirect(url_for('user.forgotPassword'))
    else:
        return render_template('forgot-password.html')


@user.route("/resetpassword", methods=['GET', "POST"])
def resetOTP():
    if request.method == "POST":
        if 'hc_user_otp_expiring_time' in session and 'hc_user_email' in session and 'hc_user_reset_otp' in session:
            pass
        else:
            flash('Something went wrong! please try again later', 'error')
            return redirect(url_for('user.forgotPassword'))
        new_password = request.form['new-password']
        confirm_new_password = request.form['confirm-new-password']
        otp = request.form['otp']
        now = datetime.now()
        if now > session['hc_user_otp_expiring_time']:
            session.pop('hc_user_otp_expiring_time')
            session.pop('hc_user_email')
            session.pop('hc_user_reset_otp')
            flash('OTP is expired!', 'error')
        else:
            sotp = session['hc_user_reset_otp']
            semail = session['hc_user_email']
            if otp == sotp:
                if new_password == confirm_new_password:
                    cur = db.connection.cursor()
                    try:
                        update_result = cur.execute("UPDATE users SET users.password=%s WHERE email=%s", (
                            bcrypt.generate_password_hash(new_password).decode("utf-8"), semail))
                    except:
                        cur.close()
                        abort(500)
                    if update_result:
                        cur.connection.commit()
                        cur.close()
                        session.pop('reset_otp', None)
                        session.pop('email', None)
                        session.pop('generated_time', None)
                        flash('Password reset complete!', 'success')
                        return redirect('signin')
                    else:
                        flash('Something went wrong, please try again', 'error')
                else:
                    flash('Passwords does not match!', 'error')
                return redirect(url_for('user.resetOTP'))
            else:
                flash('Incorrect OTP!', 'error')
                return redirect(url_for('user.resetOTP'))
        return redirect(url_for('user.forgotPassword'))
    else:
        try:
            if session['hc_user_reset_otp']:
                return render_template('reset-otp.html')
        except:
            abort(403)


@user.route("/myaccount/<string:user>")
@ user_login_required
def userAccount(user):
    cur = db.connection.cursor()
    data = getUserById(session['user_id'], url_for('user.signin'))
    if data['name'] == user:
        cur.close()
        return render_template('useraccount.html', data=data)
    else:
        cur.close()
        abort(401)


@user.route("/<string:user>/wishlist")
@ user_login_required
def yourWishlist(user):
    if user == session['name']:
        pass
    else:
        abort(401)
    cur = db.connection.cursor()
    try:
        result = cur.execute(
            "SELECT * from products JOIN wishlists ON products.product_id=wishlists.product_id WHERE wishlists.user_id = %s",
            (session["user_id"],),
        )
    except:
        cur.close()
        abort(500)
    if result:
        data = cur.fetchall()
    else:
        data = "no products"
    cur.close()
    return render_template("wishlist.html", data=data)


@user.route("/products", methods=["GET"])
def products():
    keyword = request.args["keyword"]
    sort = request.args["sort"]
    cur = db.connection.cursor()
    if not keyword == "all":
        if sort == "True":
            sql = "SELECT * FROM products WHERE product_type REGEXP '%s|%s|%s' ORDER BY price ASC" % (
                keyword, keyword[:3], keyword[:-3])
            try:
                result = cur.execute(sql)
            except:
                cur.close()
                abort(500)
        else:
            sql = "SELECT * FROM products WHERE product_type REGEXP '%s|%s|%s'" % (
                keyword, keyword[:3], keyword[:-3])
            try:
                result = cur.execute(sql)
            except:
                cur.close()
                abort(500)
    else:
        try:
            if sort == "True":
                result = cur.execute(
                    "SELECT * FROM products ORDER BY price ASC")
            else:
                result = cur.execute("SELECT * FROM products")
        except:
            cur.close()
            abort(500)
    if result:
        data = cur.fetchall()
        nbrOfProducts = len(data)
        cur.close()
        return render_template("products.html", data=data, nbrOfProducts=nbrOfProducts, keyword=keyword, sort=sort)
    else:
        data = "no product"
        return render_template("products.html", data=data, nbrOfProducts=0)


@user.route("/view/product/<int:id>/")
def product(id):
    cur = db.connection.cursor()
    try:
        result = cur.execute(
            "SELECT * FROM products WHERE product_id=(%s)", (id,))
    except:
        abort(500)
    if result:
        productinfo = cur.fetchone()
    else:
        productinfo = 'deleted'
    return render_template("product.html", product=productinfo)


@user.route('/rate/product/<int:id>', methods=['POST', 'GET'])
def rateProduct(id):
    if request.method == 'POST':
        rating = request.form['rating']
        o_id = request.form['order-id']
        try:
            review = request.form['review']
        except:
            pass
        if review:
            pass
        else:
            review = 0
        cur = db.connection.cursor()
        try:
            if cur.execute("SELECT * FROM products WHERE product_id=%s", (id,)):
                p_data = cur.fetchone()
                if p_data:
                    pass
                else:
                    flash("Product doesn't exists anymore!", "error")
                    cur.close()
                    return redirect(url_for('user.yourOrders', user=session['name']))
        except:
            cur.close()
            abort(404)
        try:
            cur.execute("INSERT INTO ratings_reviews VALUES (%s,%s,%s,%s,%s,CURRENT_DATE())",
                        (session['user_id'], id, o_id, rating, review))
            new_t_rating = int(p_data['total_ratings']) + int(rating)
            new_nbr_of_raters = int(p_data['number_of_raters'])+1
            new_rating = new_t_rating/new_nbr_of_raters
            new_rating = round(new_rating, 1)
            cur.execute("UPDATE products SET total_ratings=%s, number_of_raters=%s,rating=%s WHERE product_id=%s",
                        (new_t_rating, new_nbr_of_raters, new_rating, id))
            cur.execute(
                "UPDATE orders SET is_rated=1, rating=%s WHERE order_id=%s", (rating, o_id))
            cur.connection.commit()
            cur.close()
            flash(p_data['product_name']+" rated!", 'success')
            return redirect(url_for('user.yourOrders', user=session['name']))
        except:
            cur.close()
            abort(500)

    else:
        return abort(403)


@user.route("/<string:user>/addaddress", methods=["POST", "GET"])
@ user_login_required
def addAddress(user):
    if not user == session['name']:
        err = 'Invalid URL!'
        return render_template('error.html', err=err)
    if request.method == "POST":
        fullName = request.form["full-name"]
        mobile = request.form["mobile-number"]
        pin = request.form["pin-number"]
        house = request.form["house"]
        area = request.form["area"]
        landmark = request.form["landmark"]
        town = request.form["town"]
        state = request.form["state"]
        address = house+" \n"+area+" \n" + \
            landmark+" \n"+town+" \n"+state
        address_id = 'UAD_'+str(session['user_id']) + \
            str(math.ceil((random()*randint(0, 9))*10))
        cur = db.connection.cursor()
        try:
            result = cur.execute("INSERT INTO addresses (address_id,user_id,full_name,mobile,address,pin) VALUES (%s,%s,%s,%s,%s,%s)", (
                address_id, session["user_id"], fullName, mobile, address, pin))
        except:
            abort(500)
        if result:
            cur.connection.commit()
            flash("Address added", "success")
            return redirect(url_for("user.yourAddresses", user=session["name"]))
        else:
            flash("Something went wrong try again!", "error")
        cur.close()
    return render_template("add-address.html")


@user.route("/wishlist/<string:product>/<int:productid>/")
@ user_login_required
def addToWishlist(product, productid):
    cur = db.connection.cursor()
    isPresent = cur.execute(
        "SELECT * FROM wishlists where user_id=%s AND product_id=%s",
        (session["user_id"], productid),
    )
    if not isPresent:
        try:
            result = cur.execute(
                "INSERT INTO wishlists (user_id,product_id) VALUES (%s,%s)", (session["user_id"], productid),)
        except:
            abort(500)
        if result:
            flash("Successfully added the product into your wishlist", "success")
            cur.connection.commit()
        else:
            flash("Something went wrong try to add later!", "error")
        cur.close()
        return redirect(url_for("user.product", id=productid))
    else:
        flash("Product is already in wishlist", "error")
        return redirect(url_for("user.product", id=productid))


@user.route("/<string:user>/addresses")
@ user_login_required
def yourAddresses(user):
    if user == session['name']:
        pass
    else:
        abort(401)
    addresses = ""
    cur = db.connection.cursor()
    result = cur.execute(
        "SELECT * FROM addresses WHERE user_id=(%s)", (session["user_id"],)
    )
    if result:
        addresses = cur.fetchall()
        return render_template("your-addresses.html", addresses=addresses)
    else:
        return render_template("your-addresses.html", addresses=addresses)
    cur.close()


@user.route("/<string:user>/removeaddress", methods=["GET"])
@ user_login_required
def removeAddresses(user):
    if user == session['name']:
        pass
    else:
        abort(401)
    if request.method == "GET":
        addressId = request.args["address-id"]
        cur = db.connection.cursor()
        try:
            result = cur.execute(
                "DELETE FROM addresses WHERE address_id=(%s)", (addressId,))
        except:
            abort(401)
        if result:
            cur.connection.commit()
            flash("Address removed successfully", "success")
        else:
            flash("Something went wroung")
        cur.close()
        return redirect(url_for("user.yourAddresses", user=user))


@user.route("/<string:user>/orders")
@ user_login_required
def yourOrders(user):
    if user == session['name']:
        pass
    else:
        abort(401)
    try:
        cur = db.connection.cursor()
        res = cur.execute(
            "SELECT * FROM orders LEFT JOIN cancel_requests ON orders.order_id=cancel_requests.order_id WHERE orders.user_id=%s ORDER BY is_packed,is_dispatched,is_delivered DESC", (session["user_id"],),)
    except:
        abort(500)
    if res:
        orders = cur.fetchall()
    else:
        orders = "no orders"
    cur.close()
    return render_template("your-orders.html", orders=orders)


@user.route("/yourorders/requestcancellation", methods=['POST', 'GET'])
@ user_login_required
def requestCancelation():
    order_id = ''
    if request.method == 'POST':
        try:
            order_id = request.form['order_id']
            return render_template('order-cancel-request.html', id=order_id)
        except:
            err = 'Unauthorized access!'
            return render_template('error.html', err=err)
    else:
        order_id = request.args['order_id']
        if not order_id == '':
            reason = request.args['reason']
            if reason == 'others':
                reason = request.args['reason-desc']
            cur = db.connection.cursor()
            try:
                canid = 'can'+order_id
                cur.execute(
                    "UPDATE orders SET cancel_request=1,current_status='Cancellation requested' WHERE order_id=%s", (order_id,))
                cur.execute("INSERT INTO cancel_requests (canreq_id,order_id,user_id,reason) VALUES (%s,%s,%s,%s)",
                            (canid, order_id, session['user_id'], reason))
                cur.execute(
                    "SELECT * FROM orders JOIN products ON products.product_id=orders.product_id JOIN users ON users.user_id=orders.user_id JOIN addresses ON orders.address_id=addresses.address_id JOIN sellers ON sellers.seller_id=orders.seller_id LEFT JOIN cancel_requests ON cancel_requests.order_id=orders.order_id WHERE orders.order_id=%s", (order_id,))
                mail_data = cur.fetchone()
            except:
                abort(500)
            mail_msg = Message('Request for cancellation',
                               sender="rur209@gmail.com", recipients=["rur209@gmail.com"])
            mail_msg.html = render_template(
                'mails/order-cancel-mail.html', reason=reason, data=mail_data, brand='seller')
            # try:
            #     mail.send(mail_msg)
            # except:
            #     flash('Error occured please try again later', 'error')
            #     cur.close()
            #     return render_template('order-cancel-request.html')
            cur.connection.commit()
            return redirect(url_for('user.yourOrders', user=session['name']))
        else:
            abort(401)
    return render_template('order-cancel-request.html')


@user.route("/wishlist/remove/<int:productid>")
@ user_login_required
def removeFromWishlist(productid):
    cur = db.connection.cursor()
    try:
        result = cur.execute(
            "DELETE FROM wishlists WHERE user_id=%s AND product_id=%s", (session["user_id"], productid),)
    except:
        abort(500)
    if result:
        cur.connection.commit()
        cur.close()
        flash("Product removed from wishlist", "success")
        return redirect(url_for("user.yourWishlist", user=session["name"]))


@user.route("/<string:user>/deleteaccount", methods=["GET", "POST"])
@ user_login_required
def deleteAccount(user):
    if user == session['name']:
        pass
    else:
        abort(401)
    if request.method == "POST":
        reason = request.form['select-reason']
        if reason == 'Others':
            reason = request.form["delete-reason"]
        confirm_password = request.form["password-to-delete"]

        cur = db.connection.cursor()
        data = getUserById(session['user_id'], url_for(
            'user.deleteAccount', user=session['name']))
        dbpassword = data["password"]
        if bcrypt.check_password_hash(dbpassword, confirm_password):
            try:
                cur.execute(
                    "SELECT is_delivered,is_cancelled FROM orders WHERE user_id=%s ORDER BY ordered_on DESC;", (session['user_id'],))
                data = cur.fetchall()
            except:
                abort(500)
            for d in data:
                if not d['is_delivered'] and not d['is_cancelled']:
                    flash(
                        'You can only delete your account after of your orders are shipped, You can cancel and delete', 'error')
                    cur.close()
                    return redirect(url_for('user.yourOrders', user=user))
            try:
                if cur.execute("INSERT INTO `user_feedbacks`(`user_id`,`name`, `feedback_type`, `feedback`,`made_on`) VALUES (%s,%s,'account deletion',%s,%s)", (session["user_id"], session['name'], reason, getDateTime())):
                    if cur.execute("DELETE FROM users WHERE user_id=(%s)", (session['user_id'],)):
                        cur.connection.commit()
                        cur.close()
                        session.pop('user_id')
                        session.pop('name')
                        session.pop('mail')
                        session.pop('logged_in')
                        session.pop('buying_product_id')
                        return redirect(url_for("user.register"))
                    else:
                        flash(
                            'Something went wrong with server! please try again later', 'error')
                        cur.close()
                        return redirect(url_for('user.deleteAccount', user=user))
                else:
                    flash(
                        'Something went wrong with server! please try again later', 'error')
                    cur.close()
                    return redirect(url_for('user.deleteAccount', user=user))
            except:
                abort(500)
        else:
            cur.close()
            flash("Password incorrect!", "error")
    return render_template("delete-account.html")


@user.route("/logout")
def logout():
    session.pop('user_id')
    session.pop('name')
    session.pop('mail')
    session.pop('logged_in')
    session.pop('buying_product_id')
    flash("Logout successful", "success")
    return redirect("signin")
