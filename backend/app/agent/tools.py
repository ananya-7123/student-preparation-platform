def get_company_details(company_name: str) -> dict:
    """
    Mock function to get general company details.
    Later, this will query the PostgreSQL database.
    """
    company_name = company_name.lower()
    
    # Mock database data
    mock_db = {
        "tcs": {"name": "TCS", "industry": "IT Services", "description": "Tata Consultancy Services is a global leader in IT services."},
        "accenture": {"name": "Accenture", "industry": "Consulting & IT", "description": "Accenture is a global professional services company."},
    }
    
    return mock_db.get(company_name, {"error": f"Company '{company_name}' not found in database."})


def get_eligibility(company_name: str) -> dict:
    """
    Mock function to get eligibility criteria for a company.
    """
    company_name = company_name.lower()
    
    mock_db = {
        "tcs": {"cgpa_cutoff": 6.0, "backlogs_allowed": 0, "branches": "All B.Tech branches"},
        "accenture": {"cgpa_cutoff": 6.5, "backlogs_allowed": 0, "branches": "All B.Tech branches"},
    }
    
    return mock_db.get(company_name, {"error": f"Eligibility criteria for '{company_name}' not found."})


def get_selection_process(company_name: str) -> dict:
    """
    Mock function to get the recruitment/selection process for a company.
    """
    company_name = company_name.lower()
    
    mock_db = {
        "tcs": {"rounds": ["Written Test (Aptitude + Coding)", "Technical Interview", "HR Interview"]},
        "accenture": {"rounds": ["Cognitive & Technical Assessment", "Coding", "Communication Test", "Interview"]},
    }
    
    return mock_db.get(company_name, {"error": f"Selection process for '{company_name}' not found."})
