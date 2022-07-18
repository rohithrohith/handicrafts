from artshop import create_flask
from flask import render_template

app = create_flask()


# ERROR HANDLERS
@app.errorhandler(404)
def notFound(e):
    return render_template('error-handlers/404.html')


@app.errorhandler(500)
def serverError(e):
    return render_template('error-handlers/500.html')


@app.errorhandler(403)
def forbidden(e):
    return render_template('error-handlers/403.html')


@app.errorhandler(401)
def forbidden(e):
    return render_template('error-handlers/401.html')


############# DRIVER ################
if __name__ == "__main__":
    app.run(port=9000, debug=True)
