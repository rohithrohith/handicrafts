import os
from flask import Flask, render_template, redirect, url_for, flash, request, session, abort
from functools import wraps
from datetime import datetime
from artshop.Blue_prints.requisites import getDateTime
from dotenv import load_dotenv
from flask_mysqldb import MySQL
load_dotenv()
admin = Flask(__name__)
admin.config['MAIL_SERVER'] = "smtp.gmail.com"
admin.config['MAIL_PORT'] = 465
admin.config['MAIL_USERNAME'] = "rur209@gmail.com"
admin.config['MAIL_USE_SSL'] = True
admin.config['MAIL_USE_TLS'] = False
admin.config['UPLOAD_FOLDER'] = "artshop/static/productImages/"
admin.config['SECRET_KEY'] = "dev"
admin.config['MYSQL_USER'] = "root"
admin.config['MYSQL_DB'] = "handicrafts"
admin.config['MYSQL_HOST'] = "127.0.0.1"
admin.config['MYSQL_PORT'] = 3306
admin.config['MYSQL_CURSORCLASS'] = "DictCursor"
admin.config["MAIL_PASSWORD"] = os.getenv('MAIL_PASSWORD')
admin.config["MYSQL_PASSWORD"] = os.getenv('MYSQL_PASSWORD')

db = MySQL(admin)


@admin.context_processor
def utility_processor():
    def isPending():
        cur = db.connection.cursor()
        if cur.execute("SELECT is_pending FROM admin WHERE admin_id=%s", (session['hc_admin_id'],)):
            data = cur.fetchone()['is_pending']
            if data:
                return True
            return False
    return dict(isPending=isPending)


def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not "is_hc_admin_signin" in session:
            flash("You need to signin to access this page!", "error")
            return redirect(url_for("index"))
        else:
            return f(*args, **kwargs)

    return decorated_function


@admin.errorhandler(500)
def serverError(e):
    return render_template('/adminTemplates/errorHandlers/500.html')


@admin.errorhandler(404)
def notFound(e):
    return "NOT FOUND!"


@admin.errorhandler(403)
def notFound(e):
    return "FORBIDDEN!"


@admin.route('/admin/signin', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        aid = request.form['admin-id']
        apassword = request.form['ad-password']
        cur = db.connection.cursor()
        try:
            if cur.execute("SELECT * FROM admin WHERE admin_id=%s", (aid,)):
                data = cur.fetchone()
                if data:
                    if apassword == data['password']:
                        session['is_hc_admin_signin'] = True
                        session['hc_admin_id'] = data['admin_id']
                        session['hc_admin_name'] = data['last_name'] + \
                            ', ' + data['first_name']
                        flash('Signin complete', 'success')
                        return redirect(url_for('adminPage'))
                    else:
                        flash('Password incorrect!', 'error')
                        return render_template('/adminTemplates/admin-user-signin.html')
            flash('User does not exists!', 'error')
        except:
            flash('Server error!', 'error')
    return render_template('/adminTemplates/admin-user-signin.html')


@admin.route('/admin/home')
@admin_login_required
def adminPage():
    cur = db.connection.cursor()
    try:
        if cur.execute("SELECT * FROM verification_requests JOIN seller_details ON seller_details.seller_id=verification_requests.seller_id WHERE is_handled=0"):
            v_data = cur.fetchall()
            return render_template('/adminTemplates/admin-page.html', v_data=v_data)
        else:
            v_data = 'no data'
            return render_template('/adminTemplates/admin-page.html', v_data=v_data)
    except:
        cur.close()
        abort(500)


@admin.route('/admin/handle', methods=['POST', 'GET'])
@admin_login_required
def handleVerificationRequest():
    if request.method == 'POST':
        sid = request.form['seller-id']
        adid = request.form['admin-id']
        try:
            cur = db.connection.cursor()
            if cur.execute("UPDATE verification_requests SET handled_by=%s,is_handled=1 WHERE seller_id=%s", (adid, sid)):
                cur.connection.commit()
                cur.close()
                return redirect(url_for('viewIdentityProofs', id=sid))
            else:
                flash('Error occured while processing your request!', 'error')
                return redirect(url_for('adminPage'))
        except:
            abort(500)


@admin.route('/admin/pending')
@admin_login_required
def pendingWork():
    # try:
    cur = db.connection.cursor()
    if cur.execute("SELECT * FROM verification_requests WHERE is_handled=1 AND is_responded=0 AND handled_by=%s", (session['hc_admin_id'],)):
        data = cur.fetchone()
        cur.close()
        return redirect(url_for('viewIdentityProofs', id=data['seller_id']))
    else:
        flash('No pending work!', 'success')
        cur.close()
        return redirect(url_for('adminPage'))
    # except:
    #     abort(500)


@admin.route('/admin/view/<string:id>')
@admin_login_required
def viewIdentityProofs(id):
    cur = db.connection.cursor()
    try:
        if cur.execute("SELECT * FROM seller_details JOIN sellers ON sellers.seller_id=seller_details.seller_id WHERE seller_details.seller_id=%s", (id,)):
            data = cur.fetchone()
            cur.close()
            return render_template('/adminTemplates/viewinfo.html', data=data)
        else:
            flash('Seller does not exists anymore!', 'error')
            cur.close()
            return redirect(url_for('adminPage'))
    except:
        cur.close()
        abort(500)


@admin.route('/admin/verification/response', methods=['POST'])
@admin_login_required
def verificationResponse():
    if request.method == 'POST':
        response = request.form['response']
        sid = request.form['seller-id']
        if response == 'accept':
            cur = db.connection.cursor()
            try:
                if cur.execute("UPDATE sellers SET verification_status='verified', is_identity_verified=1,is_gst_verified=1,verified_on=%s WHERE seller_id=%s", (getDateTime(), sid)):
                    if cur.execute("UPDATE verification_requests SET verified_on=%s,is_responded=1 WHERE seller_id=%s", (getDateTime(), sid)):
                        if cur.execute("UPDATE admin SET is_pending=0 WHERE admin_id=%s", (session['hc_admin_id'],)):
                            cur.connection.commit()
                            cur.close()
                            return redirect(url_for('adminPage'))
                flash('Seller does not exists anymore!', 'error')
                cur.close()
                return redirect(url_for('adminPage'))
            except:
                cur.close()
                abort(500)
        else:
            cur = db.connection.cursor()
            try:
                if cur.execute("SELECT * FROM seller_details WHERE seller_id=%s", (sid,)):
                    data = cur.fetchone()
                    try:
                        i_remove_path = "/static/identityProofs/" + \
                            data['identity_proof']
                        s_remove_path = "/static/sellerSignatures/" + \
                            data['signature']
                        os.remove(i_remove_path)
                        os.remove(s_remove_path)
                    except:
                        flash('Error occured while deleting proof files!', 'error')
                        cur.close()
                        return redirect(url_for('adminPage'))
                else:
                    flash('Seller does not exists anymore!', 'error')
                    cur.close()
                    return redirect(url_for('adminPage'))
                if cur.execute("UPDATE sellers SET verification_status='verificationDeclined',is_identity_submitted=0 WHERE seller_id=%s", (sid,)):
                    if cur.execute("DELETE FROM verification_requests WHERE seller_id=%s", (sid,)):
                        cur.connection.commit()
                        cur.close()
                        return redirect(url_for('adminPage'))
                flash('Seller does not exists anymore!', 'error')
                cur.close()
                return redirect(url_for('adminPage'))
            except:
                cur.close()
                abort(500)


@admin.route('/admin/reviews')
@admin_login_required
def reviews():
    try:
        is_filter = request.args['filter']
    except KeyError as err:
        abort(404)
    if is_filter == 'True':
        cur = db.connection.cursor()
        start_month_date = datetime.now()
        start_month_date = start_month_date.strftime('%Y-%m')
        start_month_date = str(start_month_date)+'-01'
        sql = "SELECT * FROM ratings_reviews JOIN orders ON orders.order_id=ratings_reviews.order_id WHERE ratings_reviews.rated_on > '%s' ORDER BY ratings_reviews.rated_on DESC" % (
            start_month_date,)
        try:
            if cur.execute(sql):
                data = cur.fetchall()
            else:
                data = 'no data'
        except:
            abort(500)
        cur.close()
        return render_template('adminTemplates/reviews.html', data=data, is_filter='True')
    else:
        cur = db.connection.cursor()
        try:
            if cur.execute("SELECT * FROM ratings_reviews JOIN orders ON orders.order_id=ratings_reviews.order_id ORDER BY ratings_reviews.rated_on DESC"):
                data = cur.fetchall()
            else:
                data = 'no data'
        except:
            abort(500)
        cur.close()
        return render_template('adminTemplates/reviews.html', data=data, is_filter='False')


@admin.route('/admin/feedbacks')
@admin_login_required
def feedbacks():
    try:
        account_type = request.args['type']
    except KeyError as err:
        abort(404)
    if account_type == 'user':
        cur = db.connection.cursor()
        if cur.execute("SELECT * FROM user_feedbacks LEFT JOIN users ON users.user_id=user_feedbacks.user_id ORDER BY made_on DESC"):
            udata = cur.fetchall()
        else:
            udata = 'no data'
        cur.close()
        return render_template('adminTemplates/feedbacks.html', udata=udata, accType=account_type)
    elif account_type == 'seller':
        cur = db.connection.cursor()
        if cur.execute("SELECT * FROM seller_feedbacks LEFT JOIN sellers ON sellers.seller_id=seller_feedbacks.seller_id ORDER BY made_on DESC"):
            sdata = cur.fetchall()
        else:
            sdata = 'no data'
        cur.close()
        return render_template('adminTemplates/feedbacks.html', sdata=sdata, accType=account_type)
    else:
        abort(403)


@admin.route('/admin/view/product/<string:id>')
@admin_login_required
def viewProduct(id):
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
    return render_template("adminTemplates/product.html", product=productinfo)


@admin.route('/admin/logout')
@admin_login_required
def adminLogout():
    session.pop('is_hc_admin_signin')
    session.pop('hc_admin_id')
    session.pop('hc_admin_name')
    flash('Logout successful', 'success')
    return redirect(url_for('index'))


if __name__ == "__main__":
    admin.run(debug=True, port=8000)
