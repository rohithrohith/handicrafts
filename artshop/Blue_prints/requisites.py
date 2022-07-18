import shutil
import os
from flask import session, redirect, render_template, flash, url_for
from functools import wraps
from datetime import datetime
from flask_mysqldb import MySQL
import base64
import math
from random import random


def getDateTime():
    from datetime import datetime
    timedateStr = datetime.now()
    timedateStr = timedateStr.strftime('%d-%b-%Y, %I:%M %p')
    return timedateStr


def move_file(fn, cfn):
    path = 'D:/xammp/htdocs/ArtShop/'+fn
    copy_file_path = 'D:/xammp/htdocs/ArtShop/'+cfn
    dpath = 'D:/xammp/htdocs/ArtShop/bills'
    copy_file_dpath = 'D:/xammp/htdocs/ArtShop/bill_copies'
    try:
        shutil.move(path, dpath)
        shutil.move(copy_file_path, copy_file_dpath)
        return True
    except:
        os.remove(path)
        os.remove(copy_file_path)
        return False


def user_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not "logged_in" in session:
            flash("You need to signin to access this page!", "error")
            return redirect(url_for("user.signin"))
        else:
            return f(*args, **kwargs)

    return decorated_function


def seller_login_required(f):
    @wraps(f)
    def seller_decorated_function(*args, **kwargs):
        if not "is_seller_signined" in session:
            flash("You need to signin to access this page!", "error")
            return redirect(url_for("seller.sellerSignin"))
        else:
            return f(*args, **kwargs)

    return seller_decorated_function


def getUserById(id, returnUrl):
    from artshop import create_flask
    db = MySQL(create_flask())
    cur = db.connection.cursor()
    try:
        res = cur.execute("SELECT * FROM users WHERE user_id=%s", (id,))
    except:
        cur.close()
        abort(500)
    if res:
        data = cur.fetchone()
        cur.close()
        return data
    else:
        cur.close()
        flash('Something went wrong! please try again later', 'error')
        return redirect(returnUrl)


def get_image_file_as_base64_data(file):
    with open(file, 'rb') as image_file:
        bimage = base64.b64encode(image_file.read())
        return bimage.decode('utf8')


def allowed_img(filename):
    return "." in filename and filename.rsplit(".", 1)[1] in allowed_extentions


def generateOTP():
    characters = "0987654321"
    otp = ''
    for i in range(6):
        otp = otp + str((characters[math.floor(random()*len(characters))]))
    return otp


def start_month_date():
    start_month_date = datetime.now()
    start_month_date = start_month_date.strftime('%Y-%m')
    start_month_date = str(start_month_date)+'-01'
    return start_month_date


allowed_extentions = {"png", "jpg", "jpeg", "jfif", "pdf"}
