import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    print(session["user_id"])

    return render_template("index.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        symbol = request.form.get("symbol")
        amount = request.form.get("shares")

        if not symbol:
            return apology("missing symbol")
        if not amount or not amount.isdigit() or int(amount) < 1:
            return apology("invalid shares")

        amount = int(amount)
        quote = lookup(symbol)

        if not quote:
            return apology("invalid symbol")

        price = quote["price"] * amount
        uid = session["user_id"]
        cash = db.execute("SELECT cash FROM users WHERE id = ?", uid)[0]["cash"]

        if price > cash:
            return apology("can't afford")

        db.execute("BEGIN TRANSACTION;")

        portfolio_id = db.execute(
            """
        SELECT id FROM portfolio
        WHERE user_id = ? AND symbol = ?;
        """,
            uid,
            symbol,
        )

        if portfolio_id:
            portfolio_id = portfolio_id[0]["id"]
            db.execute(
                """
                UPDATE portfolio
                SET shares = shares + ?
                WHERE user_id = ? AND symbol = ?;
                """,
                amount,
                uid,
                symbol,
            )

        else:
            portfolio_id = db.execute(
                "INSERT INTO portfolio (user_id, symbol, shares) VALUES (?, ?, ?);",
                uid,
                symbol,
                amount,
            )

        db.execute(
            """
            INSERT INTO history (user_id, portfolio_id, symbol, shares)
            VALUES (?, ?, ?, ?);
            """,
            uid,
            portfolio_id,
            symbol,
            amount,
        )

        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?;", price, uid)

        db.execute("COMMIT;")

        redirect("/")

    elif request.method == "GET":
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("missing symbol")

        res = lookup(request.form.get("symbol"))

        if res:
            return render_template("quote-success.html", data=res)

        else:
            return apology("invalid symbol")

    elif request.method == "GET":
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("missing username", 400)

        elif (
            len(
                db.execute(
                    "SELECT * FROM users WHERE username = ?",
                    request.form.get("username"),
                )
            )
            == 1
        ):
            return apology("username is not available", 400)

        elif not request.form.get("password"):
            return apology("missing password", 400)

        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("password don't match", 400)

        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            request.form.get("username"),
            generate_password_hash(request.form.get("password")),
        )

        session["user_id"] = db.execute(
            "SELECT id FROM users WHERE username = ?", request.form.get("username")
        )[0]["id"]

        return redirect("/")

    elif request.method == "GET":
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")
