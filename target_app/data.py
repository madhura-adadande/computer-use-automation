MEMBERS = {
    "12345": {"id": "12345", "name": "John Hartwell", "email": "j.hartwell@email.com", "phone": "617-555-0142", "accounts": [{"account_no": "SAV-001", "type": "Savings", "balance": 4823.17}, {"account_no": "CHK-002", "type": "Checking", "balance": 1204.55}]},
    "67890": {"id": "67890", "name": "Maria Delgado", "email": "m.delgado@email.com", "phone": "617-555-0198", "accounts": [{"account_no": "SAV-003", "type": "Savings", "balance": 12450.00}]},
    "99999": {"id": "99999", "name": "Test Locked User", "email": "locked@email.com", "phone": "000-000-0000", "accounts": [], "locked": True}
}

def get_member(member_id):
    return MEMBERS.get(member_id)

def get_all_members():
    return MEMBERS
