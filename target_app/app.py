from flask import Flask, render_template, request, redirect, url_for, session
from data import get_member
import os

app = Flask(__name__)
app.secret_key = "dev-secret-key"

# ── Login ──────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "officer" and password == "pass123":
            session["user"] = username
            return redirect(url_for("search"))
        else:
            error = "Invalid credentials. Please try again."
    return render_template("login.html", error=error)

# ── Member Search ──────────────────────────────────────────────────────────────
@app.route("/search", methods=["GET", "POST"])
def search():
    if "user" not in session:
        return redirect(url_for("login"))
    error = None
    if request.method == "POST":
        member_id = request.form.get("member_id", "").strip()
        member = get_member(member_id)
        if not member:
            error = f"No member found with ID: {member_id}"
        elif member.get("locked"):
            error = f"Member {member_id} account is locked. Contact supervisor."
        else:
            return redirect(url_for("member_detail", member_id=member_id))
    return render_template("search.html", error=error)

# ── Member Detail ──────────────────────────────────────────────────────────────
@app.route("/member/<member_id>")
def member_detail(member_id):
    if "user" not in session:
        return redirect(url_for("login"))
    member = get_member(member_id)
    if not member:
        return render_template("search.html", error="Member not found.")
    return render_template("member_detail.html", member=member)

# ── New Sub-Account ────────────────────────────────────────────────────────────
@app.route("/member/<member_id>/new-account", methods=["GET", "POST"])
def new_subaccount(member_id):
    if "user" not in session:
        return redirect(url_for("login"))
    member = get_member(member_id)
    error = None
    confirmed = False
    if request.method == "POST":
        account_type = request.form.get("account_type")
        initial_deposit = request.form.get("initial_deposit", "").strip()
        confirm = request.form.get("confirm")
        if not account_type:
            error = "Please select an account type."
        elif not initial_deposit or not initial_deposit.replace(".", "").isdigit():
            error = "Please enter a valid initial deposit amount."
        elif float(initial_deposit) < 25:
            error = "Minimum initial deposit is $25.00."
        elif confirm == "yes":
            confirmed = True
        else:
            return render_template("new_subaccount.html",
                                   member=member,
                                   account_type=account_type,
                                   initial_deposit=initial_deposit,
                                   show_confirm=True)
    return render_template("new_subaccount.html",
                           member=member,
                           error=error,
                           confirmed=confirmed,
                           show_confirm=False)

# ── Logout ─────────────────────────────────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)