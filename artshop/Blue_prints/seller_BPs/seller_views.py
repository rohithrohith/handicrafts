from artshop.Blue_prints.requisites import *
from artshop import create_flask
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
from flask import Blueprint
import pdfkit
import os
import math
from flask import Flask, render_template, request, session, redirect, url_for, flash, abort, make_response, send_file
from flask_mail import Mail, Message
from random import randint, random
from datetime import datetime, timedelta
from itsdangerous import URLSafeSerializer
from werkzeug.utils import secure_filename

seller = Blueprint('seller', __name__, url_prefix='/seller.handicrafts',
                   template_folder='seller_templates')

app = create_flask()
db = MySQL(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)


@seller.route('/fun')
def Fun():
    return getDateTime()

# Seller Section
@seller.route("/seller.handicrafts")
def sell():
    return render_template("sellproducts.html")


@seller.route("/signin", methods=["POST", "GET"])
def sellerSignin():
    error = ""
    if request.method == "POST":
        seller_signin_mail = request.form["signin-business-email"]
        seller_signin_password = request.form["signin-business-password"]
        cur = db.connection.cursor()
        try:
            res = cur.execute(
                "SELECT * FROM sellers WHERE seller_email=%s", (seller_signin_mail,))
        except:
            cur.close()
            abort(500)
        if res:
            data = cur.fetchone()
            dbpassword = data["seller_password"]
            if not bcrypt.check_password_hash(dbpassword, seller_signin_password):
                flash('Incorrect password!', 'error')
            else:
                session["is_seller_signined"] = True
                session["seller_name"] = data["seller_name"]
                session["seller_id"] = data["seller_id"]
                cur.close()
                return redirect(url_for("seller.sellerDashboard", businessname=data["seller_name"]))
        else:
            flash("User does not exists! please register", "error")
        cur.close()
    return render_template("seller-signin.html")


@seller.route('/forgotpassword', methods=['GET', 'POST'])
def sellerForgotPassword():
    if request.method == "POST":
        email = request.form["seller-forgot-email"]
        cur = db.connection.cursor()
        try:
            res = cur.execute(
                "SELECT * FROM sellers WHERE seller_email=%s", (email,))
        except:
            cur.close()
            abort(500)
        if res:
            otp = generateOTP()
            session["hc_seller_expiring_time"] = datetime.now() + \
                timedelta(minutes=10)
            session['hc_seller_email'] = email
            session["hc_seller_reset_otp"] = otp
            mail_msg = Message("OTP for Password reset",
                               sender="rur209@gmail.com", recipients=[email])
            mail_msg.html = render_template(
                'mails/seller-forgot-password.html', otp=otp)
            try:
                mail.send(mail_msg)
                flash('OPT sent', 'success')
                cur.close()
                return render_template("seller-reset-otp.html")
            except:
                flash('Problem sending mail, please check your email id', 'error')
        else:
            flash('Account with given E-mail address does not exist', 'error')
        cur.close()
        return redirect(url_for('seller.sellerForgotPassword'))
    else:
        return render_template("seller-forgot-password.html")


@seller.route("/resetpassword", methods=["POST", "GET"])
def sellerResetOTP():
    if request.method == "POST":
        if 'hc_seller_expiring_time' in session and 'hc_seller_email' in session and 'hc_seller_reset_otp' in session:
            pass
        else:
            flash('Something went wrong! please try again later', 'error')
            return redirect('sellerForgotPassword')
        new_password = request.form['seller-new-password']
        confirm_new_password = request.form['seller-confirm-new-password']
        otp = request.form['seller-otp']
        submited_time = datetime.now()
        if submited_time > session['hc_seller_expiring_time']:
            session.pop('hc_seller_expiring_time')
            session.pop('hc_seller_email')
            session.pop('hc_seller_reset_otp')
            flash('OTP is expired!', 'error')
        else:
            if otp == session['hc_seller_reset_otp']:
                if new_password == confirm_new_password:
                    cur = db.connection.cursor()
                    try:
                        update_result = cur.execute("UPDATE sellers SET sellers.seller_password=%s WHERE seller_email=%s", (
                            bcrypt.generate_password_hash(new_password).decode("utf-8"), session['hc_seller_email']))
                    except:
                        cur.close()
                        abort(500)
                    if update_result:
                        cur.connection.commit()
                        cur.close()
                        session.pop('hc_seller_reset_otp', None)
                        session.pop('hc_seller_email', None)
                        session.pop('hc_seller_expiring_time', None)
                        flash('Password reset complete!', 'success')
                        return redirect(url_for('seller.sellerSignin'))
                    else:
                        flash('Something went wrong, please try again', 'error')
                else:
                    flash('Passwords does not match!', 'error')
                return redirect(url_for('seller.sellerResetOTP'))
            else:
                flash('Incorrect OTP!', 'error')
                return redirect(url_for('seller.sellerResetOTP'))
        return redirect(url_for('seller.sellerForgotPassword'))
    else:
        try:
            if session['seller_reset_otp']:
                return render_template('seller-reset-otp.html')
        except:
            err = 'Unauthorised access!'
            return render_template('error.html', err=err)


@seller.route("/register/step/signup", methods=["POST", "GET"])
def sellerRegisterSellSignup():
    if request.method == "POST":
        seller_name = request.form["business-name"]
        seller_email = request.form["business-email"]
        seller_password = request.form["business-password"]
        seller_confirm_password = request.form["business-c-password"]

        if seller_password == seller_confirm_password:
            cur = db.connection.cursor()
            try:
                cur.execute(
                    "SELECT * FROM sellers WHERE seller_email=(%s)", (seller_email,))
            except:
                cur.close()
                abort(500)
            data = cur.fetchone()
            if data:
                flash("User already exist, try signing in", 'error')
                return redirect(url_for('seller.sellerSignin'))
            else:
                try:
                    cur.execute("INSERT INTO sellers (seller_name,seller_email,seller_password) VALUES (%s,%s,%s)", (
                        seller_name, seller_email, bcrypt.generate_password_hash(seller_password).decode("utf-8")))
                except:
                    cur.close()
                    abort(500)
                cur.connection.commit()
                cur.close()
                # token = s.dumps(seller_email, salt="email-verify")
                token="token"
                mail_msg = Message("Hello %s!" % (
                    seller_name), sender="rur209@gmail.com", recipients=[seller_email])
                action = "localhost:9000/seller.handicrafts/confirm/email/%s/%s" % (
                    seller_name, token)
                mail_msg.html = render_template(
                    'mails/seller-account-verify.html', action=action, user=seller_name)
                # try:
                #     mail.send(mail_msg)
                #     flash("Registration successful, you can signin now!", "success")
                #     return redirect(url_for("seller.sellerSignin"))
                # except:
                #     flash(
                #         "Please verify your account in my account section as there was a problem sending you verification link to your mail", "error")
                #     return redirect(url_for("seller.sellerSignin"))
        else:
            flash("Passwords doesn't match", 'error')
            return redirect(url_for('seller.sellerRegisterSellSignup'))
    return render_template("seller-register.html")


@seller.route("/register/step/info", methods=["POST", "GET"])
@seller_login_required
def sellerRegisterSellerInfo():
    cur = db.connection.cursor()
    if request.method == 'POST':
        sign_upload_path = 'static/sellerSignatures/'
        identity_upload_path = 'static/identityProofs/'
        gstin = request.form['gstin']
        pan = request.form['pan']
        fullName = request.form["full-name"]
        mobile = request.form["mobile-number"]
        pin = request.form["pin-number"]
        house = request.form["house"]
        area = request.form["area"]
        landmark = request.form["landmark"]
        town = request.form["town"]
        state = request.form["state"]
        provided_proof_type = request.form["ID"]
        id_nbr = request.form["ID-nbr"]
        sign_file = request.files["sign"]
        identity_file = request.files["identity"]

        if sign_file.filename == "":
            flash("No signature file selected", 'error')
            return redirect(url_for("seller.sellerRegisterSellerInfo"))
        if identity_file.filename == "":
            flash("No identity proof file selected", 'error')
            return redirect(url_for("seller.sellerRegisterSellerInfo"))
        if sign_file and allowed_img(sign_file.filename) and identity_file and "." in identity_file.filename and identity_file.filename.rsplit(".", 1)[1] in ['pdf']:
            identity_filename = fullName + \
                '_identity%s' % (session['seller_id']) + "." + \
                identity_file.filename.rsplit(".", 1)[1]
            sign_filename = fullName + \
                '_sign%s' % (session['seller_id']) + '.' + \
                sign_file.filename.rsplit(".", 1)[1]
            sign_filename = secure_filename(sign_filename)
            identity_filename = secure_filename(identity_filename)
            sign_file.save(os.path.join(sign_upload_path, sign_filename))
            identity_file.save(os.path.join(
                identity_upload_path, identity_filename))
        else:
            flash('Invalid file format!', 'error')
            cur.close()
            return redirect(url_for('seller.sellerRegisterSellerInfo'))
        address = house+" \n"+area+" \n"+landmark+" \n"+town+" \n"+state
        try:
            sdresult = cur.execute("INSERT INTO seller_details (seller_id,gstin,pan_nbr,proof_id_nbr,full_name,mobile,address,pin,signature,proof_type,identity_proof) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                   (session['seller_id'], gstin, pan, id_nbr, fullName, mobile, address, pin, sign_filename, provided_proof_type, identity_filename,))
            uresult = cur.execute(
                "UPDATE sellers SET is_identity_submitted=true,verification_status='identitySubmitted' WHERE seller_id=%s", (session['seller_id'],))
            pvupdate = cur.execute(
                "INSERT INTO verification_requests (seller_id) VALUES (%s)", (session['seller_id'],))
        except:
            cur.close()
            abort(500)
        if sdresult and uresult and pvupdate:
            cur.connection.commit()
            cur.close()
            flash('Your address proof is submitted and you will get verification results in 2-3 business days by our verification team', 'success')
            return redirect(url_for('seller.sellerAccount', businessname=session['seller_name']))
        else:
            cur.close()
            flash('Something went wrong! please try again later', 'error')
            return redirect(url_for('seller.sellerAccount', businessname=session['seller_name']))
    else:
        try:
            cur.execute(
                "SELECT is_identity_submitted FROM sellers WHERE seller_id=%s", (session['seller_id'],))
        except:
            cur.close()
            abort(500)
        is_submitted = cur.fetchone()['is_identity_submitted']
        if is_submitted:
            cur.close()
            abort(403)
        else:
            cur.close()
        return render_template('seller-signup-info.html')


@seller.route("/confirm/email/<string:name>/<string:token>")
def sellerEmailVerification(name, token):
    try:
        # email = s.loads(token, salt="email-verify")
        email = "email"
        pass
    except:
        err = "Link expired!"
        return render_template("error.html", err=err)
    cur = db.connection.cursor()
    try:
        result = cur.execute(
            "SELECT * FROM sellers WHERE seller_email=%s", (email,))
    except:
        cur.close()
        abort(500)
    if result:
        data = cur.fetchone()
        if data["is_email_verified"]:
            flash("Your account is already verified! try to signin", "error")
            cur.close()
            return redirect("sellerSignin")
        else:
            try:
                verify_result = cur.execute(
                    "UPDATE sellers SET is_email_verified=TRUE WHERE seller_email=%s", (email,))
            except:
                cur.close()
                abort(500)
            if verify_result:
                flash("Account verified!", "success")
                cur.connection.commit()
                cur.close()
                return redirect(url_for("seller.sellerSignin"))
            else:
                cur.close()
                err = "Something went wrong!"
                return render_template("error.html", err=err)
    else:
        cur.close()
        err = "Account may not exists please try again!"
        return render_template("error.html", err=err)


@seller.route("/addproduct", methods=["POST", "GET"])
@seller_login_required
def addproduct():
    cur = db.connection.cursor()
    try:
        vresult = cur.execute(
            "SELECT is_identity_verified,is_gst_verified,is_email_verified FROM sellers WHERE seller_id=%s", (session['seller_id'],))
    except:
        cur.close()
        abort(500)
    if vresult:
        verifides = cur.fetchone()
        if verifides['is_identity_verified'] and verifides['is_gst_verified'] and verifides['is_email_verified']:
            pass
        else:
            flash('Verify account E-mail and identity to add products', 'error')
            return redirect(url_for('seller.sellerAccount', businessname=session['seller_name']))
    else:
        flash('Something went wrong with server! try again later', 'error')
        return redirect(url_for('seller.sellerDashboard', businessname=session['seller_name']))

    if request.method == "POST":
        product_name = request.form["product-name"]
        product_type = request.form["product-type"]
        product_price = request.form["product-price"]
        product_quantity = request.form["product-quantity"]
        product_desc = request.form["product-desc"]
        product_artist = request.form["product-artist"]

        product_img = request.files["product-img"]
        if product_img.filename == "":
            flash("No file selected", 'error')
            return redirect(url_for("seller.addproduct"))
        if product_img and allowed_img(product_img.filename):
            filename = secure_filename(product_img.filename)
            product_img.save(os.path.join(
                app.config["UPLOAD_FOLDER"], filename))
            product_img.save(os.path.join('static/productImages/', filename))
            try:
                cur.execute(
                    "INSERT INTO products (seller_id,seller,product_name,product_type,artist,product_quantity_left,price,product_img,product_desc) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", [
                        session["seller_id"], session["seller_name"], product_name, product_type, product_artist, product_quantity, product_price, filename, product_desc, ],
                )
                cur.connection.commit()
            except:
                cur.close()
                abort(500)
            cur.close()
            return redirect(url_for("seller.sellerDashboard", businessname=session["seller_name"]))

    return render_template("addproduct.html")


@seller.route("/edit/product/<int:productId>", methods=["GET", "POST"])
def editProduct(productId):
    data = None
    cur = db.connection.cursor()
    try:
        result = cur.execute(
            "SELECT * FROM products WHERE product_id=%s", (productId,))
    except:
        cur.close()
        abort(500)
    if request.method == "GET":
        if result:
            data = cur.fetchone()
            try:
                if session["seller_id"] == data["seller_id"]:
                    cur.close()
                    return render_template("edit-product.html", data=data)
                else:
                    cur.close()
                    flash('You can only edit your products', 'error')
                    abort(404)
            except:
                cur.close()
                return redirect(url_for("seller.sellerSignin"))
        else:
            cur.close()
            flash("Something went wrong! Try again later", "error")
    else:
        if result:
            data = cur.fetchone()
            edited_name = request.form["edited-name"]
            edited_type = request.form["edited-type"]
            edited_quantity = request.form["edited-quantity"]
            edited_price = request.form["edited-price"]
            edited_desc = request.form["edited-desc"]

            if (edited_desc == data["product_desc"]and edited_name == data["product_name"]and str(edited_quantity) == str(data["product_quantity_left"])and str(edited_price) == str(data["price"])and edited_type == data["product_type"]):
                flash("No changes made", "error")
                cur.close()
                return redirect(url_for("seller.editProduct", productId=productId))
            else:
                try:
                    result = cur.execute("UPDATE products SET product_name=%s, product_type=%s,product_quantity_left=%s,price=%s,product_desc=%s WHERE product_id=%s", (
                        edited_name, edited_type, edited_quantity, edited_price, edited_desc, productId,))
                except:
                    cur.close()
                    abort(500)
                if result:
                    flash("Changes saved", "success")
                    cur.connection.commit()
                    cur.close()
                    return redirect(
                        url_for("seller.sellerDashboard",
                                businessname=session["seller_name"])
                    )
                else:
                    cur.close()
                    print("Something went wrong! please try again later", "error")
                    return redirect(url_for("seller.editProduct", productId=productId))
    cur.close()
    flash("Something went wrong! please try again later", "error")
    return render_template("edit-product.html")


@seller.route("/<string:seller>/delete/product", methods=["GET"])
@seller_login_required
def deleteProduct(seller):
    if seller == session['seller_name']:
        pass
    else:
        abort(401)
    if request.method == "GET":
        productId = request.args["product-id"]
        cur = db.connection.cursor()
        try:
            result = cur.execute(
                "DELETE FROM products WHERE product_id=(%s) AND seller_id=(%s)", (productId, session["seller_id"]),)
        except:
            cur.close()
            abort(500)
        if result:
            cur.connection.commit()
            flash("Product removed", "success")
        else:
            flash("Something went wrong!", "error")
        cur.close()
        return redirect(url_for("seller.sellerDashboard", businessname=seller))


@seller.route("/account/<string:businessname>")
@seller_login_required
def sellerAccount(businessname):
    if businessname == session['seller_name']:
        pass
    else:
        abort(401)
    cur = db.connection.cursor()
    try:
        result = cur.execute(
            "SELECT * FROM sellers WHERE seller_id=%s", (session["seller_id"],))
    except:
        cur.close()
        abort(500)
    if result:
        seller = cur.fetchone()
        cur.close()
        return render_template("seller-account.html", seller=seller)
    else:
        cur.close()
        flash("Something went wrong!", "error")
        return redirect("sellerDashboard", businessname=businessname)


@seller.route("/edit/account/<string:businessname>", methods=['POST', 'GET'])
@seller_login_required
def editSellerAccount(businessname):
    if businessname == session['seller_name']:
        pass
    else:
        abort(401)
    cur = db.connection.cursor()
    if request.method == 'GET':
        try:
            if cur.execute("SELECT * FROM sellers JOIN seller_details ON sellers.seller_id=seller_details.seller_id WHERE sellers.seller_id=%s", (session['seller_id'],)):
                data = cur.fetchone()
                cur.close()
                return render_template('seller-edit-account.html', data=data)
            else:
                flash(
                    'Something went wrong with the server! please try again later', 'error')
                cur.close()
                return redirect(url_for('seller.sellerAccount', businessname=businessname))
        except:
            cur.close()
            abort(500)
    else:
        try:
            is_editing_add = request.form['is-new-address']
        except KeyError:
            flash('No changes made', 'error')
            cur.close()
            return redirect(url_for('seller.editSellerAccount', businessname=businessname))
        fname = request.form['full-name']
        mobile = request.form['mobile-number']
        pin = request.form['pin-number']
        house = request.form['house']
        area = request.form['area']
        landmark = request.form['landmark']
        town = request.form['town']
        state = request.form['state']
        try:
            if cur.execute(
                    "SELECT * FROM seller_details WHERE seller_id=%s", (session['seller_id'],)):
                db_data = cur.fetchone()
                new_address = house+" \r\n"+area+" \r\n"+landmark+" \r\n"+town+" \r\n"+state
                if not new_address == db_data['address']:
                    if cur.execute("UPDATE seller_details SET full_name=%s,mobile=%s,pin=%s,address=%s WHERE seller_id=%s", (fname, mobile, pin, new_address, session['seller_id'])):
                        cur.connection.commit()
                        flash('Address updated', 'success')
                        cur.close()
                        return redirect(url_for('seller.sellerAccount', businessname=businessname))
                    else:
                        flash(
                            'No changes made1', 'error')
                        cur.close()
                        return redirect(url_for('seller.editSellerAccount', businessname=businessname))
                else:
                    flash('No changes made2', 'error')
                    cur.close()
                    return redirect(url_for('seller.editSellerAccount', businessname=businessname))
            else:
                flash(
                    'Something went wrong with server! please try again later', 'error')
                cur.close()
                return redirect(url_for('seller.editSellerAccount', businessname=businessname))
        except:
            abort(500)


@seller.route("/edit/name/<string:businessname>", methods=['POST', 'GET'])
@seller_login_required
def editSellerName(businessname):
    if businessname == session['seller_name']:
        pass
    else:
        abort(401)
    if request.method == 'POST':
        edited_name = request.form['edit-name']
        cur = db.connection.cursor()
        try:
            res = cur.execute(
                "SELECT seller_name FROM sellers WHERE seller_id=%s", (session['seller_id'],))
        except:
            cur.close()
            abort(500)
        if res:
            seller_name = cur.fetchone()['seller_name']
            if seller_name == edited_name:
                flash('No change made!', 'error')
                cur.close()
                return redirect(url_for('seller.editSellerAccount', businessname=businessname))
            else:
                if cur.execute("UPDATE sellers SET seller_name=%s WHERE seller_id=%s",
                               (edited_name, session['seller_id'])):
                    cur.connection.commit()
                    cur.close()
                    session['seller_name'] = edited_name
                    flash('Name changed', 'success')
                    return redirect(url_for('seller.sellerAccount', businessname=businessname))
                else:
                    abort(500)
        else:
            flash('Something went wrong! please try again later', 'error')
            cur.close()
            return redirect(url_for('seller.sellerAccount', businessname=businessname))
    else:
        abort(404)


@seller.route('/edit/password/<string:businessname>', methods=['GET', 'POST'])
@seller_login_required
def editSellerPassword(businessname):
    if businessname == session['seller_name']:
        pass
    else:
        abort(401)
    if request.method == "POST":
        cur_password = request.form["seller-current-password"]
        new_password = request.form["seller-new-password"]
        confirm_new_password = request.form["confirm-seller-new-password"]
        cur = db.connection.cursor()
        try:
            result = cur.execute(
                "SELECT * FROM sellers WHERE seller_id=(%s)", (
                    session["seller_id"],)
            )
        except:
            cur.close()
            abort(500)
        if result:
            dbpassword = cur.fetchone()["seller_password"]
            if not bcrypt.check_password_hash(dbpassword, cur_password):
                flash("Incorrect current password", "error")
            else:
                if not new_password == confirm_new_password:
                    flash("New passwords doesn't match", "error")
                else:
                    try:
                        cur.execute(
                            "UPDATE sellers set seller_password=(%s) WHERE seller_id=(%s)",
                            (
                                bcrypt.generate_password_hash(new_password),
                                session["seller_id"],
                            ),
                        )
                        cur.connection.commit()
                        cur.close()
                        flash("Password changed", "success")
                        return redirect(url_for("seller.sellerSignin"))
                    except:
                        cur.close()
                        abort(500)
        else:
            cur.close()
            flash('Something went wrong! please try again later', 'error')
            return redirect(url_for('seller.editSellerPassword', businessname=businessname))
        cur.close()
    return render_template("seller-edit-password.html")


@seller.route('/deleteaccount/<string:businessname>', methods=['GET', 'POST'])
@seller_login_required
def sellerAccountDelete(businessname):
    if businessname == session['seller_name']:
        pass
    else:
        abort(401)
    if request.method == "POST":
        reason = request.form["delete-reason"]
        confirm_password = request.form["password-to-delete"]

        cur = db.connection.cursor()
        try:
            result = cur.execute(
                "SELECT * FROM sellers WHERE seller_id=(%s)", (
                    session["seller_id"],)
            )
        except:
            cur.close()
            abort(500)
        if result:
            dbpassword = cur.fetchone()["seller_password"]
            if bcrypt.check_password_hash(dbpassword, confirm_password):
                try:
                    if cur.execute("SELECT is_delivered FROM orders WHERE seller_id=%s ORDER BY ordered_on DESC", (session['seller_id'],)):
                        data = cur.fetchall()
                        for d in data:
                            if not d['is_delivered']:
                                flash(
                                    'You can only delete your account after completion of your orders', 'error')
                                cur.close()
                                return redirect(url_for('seller.sellerOrders', businessname=businessname))
                        if cur.execute("DELETE FROM sellers WHERE seller_id=(%s)", (session["seller_id"],)):
                            if cur.execute("INSERT INTO feedbacks (seller_id,feedback_type,feedback,made_on) VALUES (%s,'account deletion',%s,%s)", (session['seller_id'], reason, getDateTime())):
                                cur.connection.commit()
                                cur.close()
                                session.clear()
                                return redirect(url_for("seller.sellerRegisterSellSignup"))
                    flash(
                        'Something went wrong with server! please try again later', 'error')
                    cur.close()
                    return redirect(url_for('seller.sellerAccountDelete', businessname=businessname))
                except:
                    cur.close()
                    abort(500)
            else:
                msg = "Password doesn't match"
                flash(msg, "error")
        else:
            flash("Something went wrong! Please try again", "error")
        cur.close()
    return render_template("seller-account-delete.html")


@seller.route("/dashboard/<string:businessname>")
@seller_login_required
def sellerDashboard(businessname):
    if businessname == session['seller_name']:
        pass
    else:
        abort(401)
    cur = db.connection.cursor()
    try:
        res = cur.execute(
            "SELECT * FROM products WHERE seller_id=%s ORDER BY times_sold DESC",
            (session["seller_id"],)
        )
    except:
        cur.close()
        abort(500)
    data = cur.fetchall()
    sql = "SELECT price FROM sold_info WHERE seller_id=%s AND delivered_on >= '%s' ORDER BY delivered_on DESC" % (
        session['seller_id'], start_month_date())
    try:
        cur.execute(sql)
    except:
        cur.close()
        abort(500)
    sold_data = cur.fetchall()
    mr = 0
    for price in sold_data:
        mr += price['price']
    is_new_orders = False
    try:
        if cur.execute("SELECT is_packed FROM orders WHERE is_packed=0 AND seller_id=%s LIMIT 1", (session['seller_id'],)):
            is_new_orders = True
        earnings = 0
        if cur.execute(
                "SELECT earnings FROM seller_details WHERE seller_id=%s", (session['seller_id'],)):
            earnings = cur.fetchone()['earnings']
    except:
        cur.close()
        abort(500)
    cur.close()
    return render_template(
        "seller-dashboard.html", businessname=businessname, data=data, mr=mr, earnings=earnings, n_orders=is_new_orders)


@seller.route('/orders/<string:businessname>', methods=['GET'])
@seller_login_required
def sellerOrders(businessname):
    if businessname == session['seller_name']:
        pass
    else:
        abort(401)
    try:
        order_filter = request.args['filter']
        filter_list = ['Not packed', 'Packed',
                       'Dispatched', 'Delivered', 'Cancelled', 'Remove filter']
        if (order_filter in filter_list):
            f_index = filter_list.index(order_filter)
            cur = db.connection.cursor()
            try:
                if f_index == 0:
                    presult = cur.execute(
                        "SELECT * FROM orders LEFT JOIN sold_info ON orders.order_id=sold_info.order_id LEFT JOIN cancel_requests ON cancel_requests.order_id=orders.order_id WHERE orders.seller_id=%s AND is_packed=0 AND is_cancelled=0 GROUP BY orders.order_id,orders.price,orders.address_id,orders.is_packed,orders.is_dispatched,orders.is_delivered,orders.is_cancelled,orders.current_status,orders.address ORDER BY is_packed ASC,is_dispatched ASC,is_delivered ASC, sold_info.delivered_on DESC", (session['seller_id'],))
                elif f_index == 1:
                    presult = cur.execute(
                        "SELECT * FROM orders LEFT JOIN sold_info ON orders.order_id=sold_info.order_id LEFT JOIN cancel_requests ON cancel_requests.order_id=orders.order_id WHERE orders.seller_id=%s AND is_packed=1 AND is_dispatched=0 AND is_delivered=0 AND is_cancelled=0 GROUP BY orders.order_id,orders.price,orders.address_id,orders.is_packed,orders.is_dispatched,orders.is_delivered,orders.is_cancelled,orders.current_status,orders.address ORDER BY is_packed ASC,is_dispatched ASC,is_delivered ASC, sold_info.delivered_on DESC", (session['seller_id'],))
                elif f_index == 2:
                    presult = cur.execute(
                        "SELECT * FROM orders LEFT JOIN sold_info ON orders.order_id=sold_info.order_id LEFT JOIN cancel_requests ON cancel_requests.order_id=orders.order_id WHERE orders.seller_id=%s AND is_dispatched=1 AND is_delivered=0 AND is_cancelled=0 GROUP BY orders.order_id,orders.price,orders.address_id,orders.is_packed,orders.is_dispatched,orders.is_delivered,orders.is_cancelled,orders.current_status,orders.address ORDER BY is_packed ASC,is_dispatched ASC,is_delivered ASC, sold_info.delivered_on DESC", (session['seller_id'],))
                elif f_index == 3:
                    presult = cur.execute(
                        "SELECT * FROM orders LEFT JOIN sold_info ON orders.order_id=sold_info.order_id LEFT JOIN cancel_requests ON cancel_requests.order_id=orders.order_id WHERE orders.seller_id=%s AND is_delivered=1 AND is_cancelled=0 GROUP BY orders.order_id,orders.price,orders.address_id,orders.is_packed,orders.is_dispatched,orders.is_delivered,orders.is_cancelled,orders.current_status,orders.address ORDER BY is_packed ASC,is_dispatched ASC,is_delivered ASC, sold_info.delivered_on DESC", (session['seller_id'],))
                elif f_index == 4:
                    presult = cur.execute(
                        "SELECT * FROM orders LEFT JOIN sold_info ON orders.order_id=sold_info.order_id LEFT JOIN cancel_requests ON cancel_requests.order_id=orders.order_id WHERE orders.seller_id=%s AND is_cancelled=1 GROUP BY orders.order_id,orders.price,orders.address_id,orders.is_packed,orders.is_dispatched,orders.is_delivered,orders.is_cancelled,orders.current_status,orders.address ORDER BY is_packed ASC,is_dispatched ASC,is_delivered ASC, sold_info.delivered_on DESC", (session['seller_id'],))
                else:
                    cur.close()
                    return redirect(url_for('seller.sellerOrders', businessname=businessname))
            except:
                cur.close()
                abort(500)
            if presult:
                order_data = cur.fetchall()
                cur.close()
                return render_template('seller-orders.html', order_data=order_data, filter=order_filter)
            else:
                order_data = 'no orders'
                cur.close()
                return render_template('seller-orders.html', order_data=order_data, filter=order_filter)
        else:
            flash('Invalid filter applied', 'error')
            return redirect(url_for('seller.sellerOrders', businessname=businessname))
    except KeyError:
        cur = db.connection.cursor()
        presult = cur.execute(
            "SELECT * FROM orders LEFT JOIN sold_info ON orders.order_id=sold_info.order_id LEFT JOIN cancel_requests ON cancel_requests.order_id=orders.order_id WHERE orders.seller_id=%s GROUP BY orders.order_id,orders.price,orders.address_id,orders.product_id,orders.product_img,orders.address,orders.is_packed,orders.is_dispatched,orders.is_delivered,orders.is_cancelled,orders.current_status ORDER BY is_packed ASC,is_dispatched ASC,is_delivered ASC, sold_info.delivered_on DESC", (session['seller_id'],))
        if presult:
            order_data = cur.fetchall()
            cur.close()
            return render_template('seller-orders.html', order_data=order_data)
        else:
            order_data = 'no orders'
            cur.close()
            return render_template('seller-orders.html', order_data=order_data)


@seller.route("/external/email/verify", methods=["GET"])
@seller_login_required
def sellerExternalVerification():
    email = request.args["email"]
    cur = db.connection.cursor()
    try:
        result = cur.execute(
            "SELECT * FROM sellers WHERE seller_id=%s", (session["seller_id"],)
        )
    except:
        cur.close()
        abort(500)
    if result:
        data = cur.fetchone()
        if data["is_verified"]:
            flash("Account is already verified", "error")
            cur.close()
            return redirect("sellerAccount", businessname=session["seller_name"])
        else:
            token = "bang"
            mail_msg = Message(
                "Hello %s!" % (data['seller_name']),
                sender="rur209@gmail.com",
                recipients=[email],
            )
            mail_msg.html = """<h2>Verify your seller account</h2>
                <a href="localhost:9000/seller.handicrafts/confirm/email/%s/%s" style="color:white; padding:10px;border-radius:5px; background:#f9246b;">Verify here</a>
                """ % (
                data['seller_name'],
                token,
            )

            try:
                mail.send(mail_msg)
                flash(
                    """Verification link is sent to your E-mail, it will be expired in two minutes. verify your account""")
                cur.close()
                return redirect(
                    url_for("seller.sellerAccount",
                            businessname=session["seller_name"])
                )
            except:
                flash('Error occured while sending mail please try again later', 'error')
                cur.close()
                return redirect(url_for("seller.sellerAccount", businessname=session["seller_name"]))
    else:
        cur.close()
        flash("Someting went wrong", "error")
        return redirect(url_for("seller.sellerAccount", businessname=session["seller_name"]))


@seller.route("/sellerlogout")
def sellerLogout():
    session.pop('seller_id')
    session.pop('seller_name')
    session.pop('is_seller_signined')
    flash("Logout successful", "success")
    return redirect(url_for('seller.sellerSignin'))


@seller.route('/cancel', methods=['POST', 'GET'])
def cancelOrder():
    if request.method == 'POST':
        orderId = request.form['order-id']
        action = request.form['action']
        if action == 'accept':
            cur = db.connection.cursor()
            try:
                result = cur.execute(
                    "SELECT * FROM orders WHERE order_id=%s", (orderId,))
            except:
                cur.close()
                abort(500)
            if result:
                data = cur.fetchone()
                if not data['is_cancelled'] and not data['is_delivered']:
                    currentDateTime = getDateTime()
                    try:
                        if cur.execute("UPDATE orders SET is_cancelled=%s,current_status='Cancelled',cancelled_on=%s WHERE order_id=%s",
                                       (not data['is_cancelled'], getDateTime(), orderId)):
                            if cur.execute("UPDATE cancel_requests SET is_responsed=1,response='accepted' WHERE order_id=%s", (orderId,)):
                                cur.connection.commit()
                                flash("Order cancelled", 'success')
                                cur.execute(
                                    "SELECT * FROM orders JOIN users ON users.user_id=orders.user_id WHERE order_id=%s", (orderId,))
                                udata = cur.fetchone()
                                user_mail_msg = Message(
                                    'Cancellation request accepted!', sender="rur209@gmail.com", recipients=[udata['email']])
                                user_mail_msg.html = render_template(
                                    'mails/can-re-response.html', response='accept', data=udata)
                                # try:
                                #     mail.send(user_mail_msg)
                                # except:
                                #     cur.close()
                                #     return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
                                cur.close()
                                return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
                            else:
                                flash(
                                    'Server error, please try again later', 'error')
                                cur.close()
                                return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
                        else:
                            flash('Server error, please try again later', 'error')
                            cur.close()
                            return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
                    except:
                        cur.close()
                        abort(500)
                else:
                    flash(
                        'You can not cancel order which has been already delivered or cancelled', 'error')
                    cur.close()
                    return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
            else:
                flash('Server error, please try again later', 'error')
                cur.close()
                return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
        else:
            cur = db.connection.cursor()
            cur.execute(
                "SELECT * FROM orders JOIN users ON users.user_id=orders.user_id WHERE order_id=%s", (orderId,))
            udata = cur.fetchone()
            try:
                if cur.execute("UPDATE orders SET current_status='Cancellation request declined' WHERE order_id=%s",
                               (orderId,)):
                    if cur.execute("UPDATE cancel_requests SET is_responsed=1,response='rejected' WHERE order_id=%s", (orderId,)):
                        cur.connection.commit()
            except:
                cur.close()
                abort(500)
            user_mail_msg = Message(
                'Cancellation request rejected!', sender="rur209@gmail.com", recipients=[udata['email']])
            user_mail_msg.html = render_template(
                'mails/can-re-response.html', data=udata)
            # try:
            #     mail.send(user_mail_msg)
            # except:
            #     cur.close()
            #     return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
            cur.close()
            return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))


@seller.route('/cancelrequest/view/<string:id>', methods=['POST', 'GET'])
def viewCancelRequest(id):
    cur = db.connection.cursor()
    try:
        cur.execute(
            "SELECT * FROM cancel_requests JOIN users ON users.user_id=cancel_requests.user_id WHERE canreq_id=%s", (id,))
        data = cur.fetchone()
    except:
        cur.close()
        abort(500)
    cur.close()
    return render_template('view-cancel-request.html', data=data)


# SELLER ACTIONS
@seller.route('/getbill', methods=['POST', 'GET'])
@seller_login_required
def getBill():
    if request.method == 'POST':
        orderId = request.form['order-id']
        cur = db.connection.cursor()
        try:
            res = cur.execute(
                "SELECT * FROM orders JOIN users ON users.user_id=orders.user_id JOIN sellers ON sellers.seller_id=orders.seller_id WHERE orders.order_id=%s", (orderId,))
            if res:
                order_data = cur.fetchone()
            else:
                flash('Order could not be found! try again later', 'error')
                cur.close()
                return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
            sres = cur.execute(
                "SELECT * FROM seller_details WHERE seller_id=%s", (order_data['seller_id'],))
            if sres:
                sadata = cur.fetchone()
            else:
                flash('Order could not be found! try again later', 'error')
                cur.close()
                return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
        except:
            cur.close()
            abort(500)
        if not order_data['is_cancelled']:
            if order_data['is_packed']:
                flash('Already packed!', 'error')
                cur.close()
                return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
        else:
            flash('Order was cancelled!', 'error')
            cur.close()
            return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
        path = 'D:/xammp/htdocs/ArtShop/artshop/static/HandicraftsLogo1.png'
        sign_path = 'artshop/static/sellerSignatures/'+sadata['signature']
        brand_image = get_image_file_as_base64_data(path)
        ele_sign = get_image_file_as_base64_data(sign_path)
        gstp = int(order_data['price'])*.18
        tp = gstp+int(order_data['price'])
        ta = tp+70
        pdf_filename = str(orderId) + '.pdf'
        copy_pdf_filename = str(orderId) + '_copy' + '.pdf'
        pdf = render_template('bill.html', data=order_data, sadata=sadata, gstp=gstp,
                              tp=tp, ta=ta, getDateTime=getDateTime, brandImage=brand_image, sign=ele_sign)
        pdf_copy = render_template('bill-copy.html', data=order_data, sadata=sadata, gstp=gstp,
                                   tp=tp, ta=ta, getDateTime=getDateTime, brandImage=brand_image, sign=ele_sign)
        try:
            pdfkit.from_string(pdf, pdf_filename)
            pdfkit.from_string(pdf_copy, copy_pdf_filename)
            pdf = pdfkit.from_string(pdf, False)
        except:
            flash('Error creating invoices! please try again later', 'error')
            cur.close()
            return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
        if not move_file(pdf_filename, copy_pdf_filename):
            flash('Something went wrong please try again!', 'error')
            cur.close()
            return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
        else:
            try:
                uresult = cur.execute(
                    "UPDATE orders SET is_packed=%s, current_status='Ready to dispatch',packed_on=%s WHERE order_id=%s", (not order_data['is_packed'], getDateTime(), orderId))
            except:
                cur.close()
                abort(500)
            if uresult:
                cur.connection.commit()
                resp = make_response(pdf)
                resp.headers['Content-Type'] = 'application/pdf'
                resp.headers['Content-Disposition'] = 'attachment; filename=%s' % (
                    pdf_filename,)
                cur.close()
                return resp
    else:
        abort(401)


@seller.route('/dispatch', methods=['GET', 'POST'])
@seller_login_required
def orderDispatch():
    if request.method == 'POST':
        orderId = request.form['order-id']
        cur = db.connection.cursor()
        try:
            cur.execute(
                "SELECT is_packed,is_dispatched,is_cancelled from orders WHERE order_id=%s", (orderId,))
            status_data = cur.fetchone()
            if status_data['is_packed']:
                if not status_data['is_cancelled']:
                    pass
                else:
                    flash('Order was cancelled!', 'error')
                    cur.close()
                    return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
            else:
                flash('Need to complete previous actions!', 'error')
                cur.close()
                return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
            cur.execute(
                "UPDATE orders SET is_dispatched=%s,current_status='Dispatched',dispatched_on=%s WHERE order_id=%s", (not status_data['is_dispatched'], getDateTime(), orderId))
            cur.connection.commit()
            cur.execute(
                "SELECT * FROM orders JOIN users ON users.user_id=orders.user_id WHERE order_id=%s", (orderId,))
            mail_data = cur.fetchone()
            user_mail_msg = Message(
                'Order dispatched', sender="rur209@gmail.com", recipients=[mail_data['email']])
            user_mail_msg.html = render_template(
                '/mails/dispatched.html', data=mail_data)
            # try:
            #     mail.send(user_mail_msg)
            # except:
            #     pass
            flash('Order status updated!', 'success')
            cur.close()
            return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
        except:
            cur.close()
            abort(500)
    else:
        err = 'Unauthorized access!'
        return render_template('error.html', err=err)


@seller.route('/deliver', methods=['GET', 'POST'])
@seller_login_required
def orderDeliver():
    if request.method == 'POST':
        orderId = request.form['order-id']
        cur = db.connection.cursor()
        try:
            cur.execute(
                "SELECT * FROM orders WHERE orders.order_id=%s", (orderId,))
            order_data = cur.fetchone()
            cur.execute("SELECT earnings FROM seller_details WHERE seller_id=%s", (
                session['seller_id'],))
            earnings = cur.fetchone()['earnings']
            new_earnings = int(earnings) + int(order_data['price'])
            if order_data['is_packed'] and order_data['is_dispatched']:
                try:
                    cur.execute(
                        "UPDATE orders SET is_delivered=%s,current_status='Product delivered',delivered_on=%s WHERE order_id=%s", (not order_data['is_delivered'], getDateTime(), orderId))
                    cur.execute(
                        "UPDATE seller_details SET earnings=%s WHERE seller_id=%s", (new_earnings, order_data['seller_id']))
                    cur.execute("INSERT INTO sold_info (order_id,seller_id,user_id,price,delivered_on) VALUES (%s,%s,%s,%s,CURRENT_DATE())",
                                (orderId, order_data['seller_id'], order_data['user_id'], order_data['price']))
                except:
                    cur.close()
                    abort(500)
                cur.connection.commit()
                cur.execute(
                    "SELECT * FROM orders JOIN users ON users.user_id=orders.user_id WHERE order_id=%s", (orderId,))
                mail_data = cur.fetchone()
                user_mail_msg = Message(
                    'Order delivered', sender="rur209@gmail.com", recipients=[mail_data['email']])
                user_mail_msg.html = render_template(
                    '/mails/delivered.html', data=mail_data)
                # try:
                #     mail.send(user_mail_msg)
                # except:
                #     pass
                flash('Order status updated!', 'success')
                cur.close()
                return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
            else:
                flash(
                    'Need to complete previous actions', 'error')
                return redirect(url_for('seller.sellerOrders', businessname=session['seller_name']))
        except:
            cur.close()
            abort(500)
    else:
        err = 'Unauthorized access!'
        return render_template('error.html', 'error')


@seller.route('/bill/download/<string:name>')
def downloadBill(name):
    pdf_file = 'D:/xammp/htdocs/ArtShop/bill_copies/' + name+'_copy.pdf'
    return send_file(pdf_file, attachment_filename=name+'_invoice.pdf', as_attachment=True)
