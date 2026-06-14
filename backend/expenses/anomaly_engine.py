import datetime
from decimal import Decimal, InvalidOperation
import re

# List of known valid system users
VALID_USERS = ['Aisha', 'Rohan', 'Priya', 'Meera', 'Sam', 'Dev']

# Hardcoded Membership Dates for Validation based on Requirements:
# Aisha, Rohan, Priya joined Feb 1st, 2026. Still active.
# Meera joined Feb 1st, 2026. Left March 31st, 2026.
# Sam joined April 15th, 2026. Still active.
# Dev visited for Goa Trip: active from Feb 1st, 2026 to March 31st, 2026.
MEMBERSHIP_DATES = {
    'Aisha': {'joined': datetime.date(2026, 2, 1), 'left': None},
    'Rohan': {'joined': datetime.date(2026, 2, 1), 'left': None},
    'Priya': {'joined': datetime.date(2026, 2, 1), 'left': None},
    'Meera': {'joined': datetime.date(2026, 2, 1), 'left': datetime.date(2026, 3, 31)},
    'Sam': {'joined': datetime.date(2026, 4, 15), 'left': None},
    'Dev': {'joined': datetime.date(2026, 2, 1), 'left': datetime.date(2026, 3, 31)},
}

# Standard Exchange rate configuration (1 USD = 83 INR)
FIXED_USD_TO_INR_RATE = Decimal('83.00')

# ==============================================================================
# ROBUST DATE PARSER
# ==============================================================================
def parse_dirty_date(date_str):
    """
    Why this exists:
    Converts various inconsistent date formats from the CSV into a Python date object.
    Supports YYYY-MM-DD, DD/MM/YYYY, and MMM DD (like Mar 14).
    """
    if not date_str or not str(date_str).strip():
        return None
    
    clean_str = str(date_str).strip()
    
    # Try YYYY-MM-DD (e.g., 2026-02-01)
    try:
        return datetime.datetime.strptime(clean_str, '%Y-%m-%d').date()
    except ValueError:
        pass
        
    # Try DD/MM/YYYY (e.g., 15/03/2026)
    try:
        return datetime.datetime.strptime(clean_str, '%d/%m/%Y').date()
    except ValueError:
        pass
        
    # Try MMM DD (e.g., Mar 14) -> Assumes context year 2026
    try:
        parsed_date = datetime.datetime.strptime(clean_str, '%b %d').date()
        return parsed_date.replace(year=2026)
    except ValueError:
        pass
        
    # Try DD MMM YYYY if any
    try:
        return datetime.datetime.strptime(clean_str, '%d %b %Y').date()
    except ValueError:
        pass

    return None


# ==============================================================================
# RESOLVE USERNAME (NAME CLEANING POLICY)
# ==============================================================================
def clean_username(name_str):
    """
    Why this exists:
    Maps noisy or misspelled usernames to official system users.
    Examples: 'priya' -> 'Priya', 'rohan ' -> 'Rohan', 'Priya S' -> 'Priya'.
    """
    if not name_str or not str(name_str).strip():
        return None
        
    name = str(name_str).strip().lower()
    
    # Exact mappings for aliases
    if name in ['priya', 'priya s', 'priyas']:
        return 'Priya'
    if name in ['rohan', 'rohan ']:
        return 'Rohan'
    if name in ['aisha']:
        return 'Aisha'
    if name in ['meera']:
        return 'Meera'
    if name in ['sam']:
        return 'Sam'
    if name in ['dev']:
        return 'Dev'
        
    # Title-case default check if it starts with valid names
    for valid in VALID_USERS:
        if name.startswith(valid.lower()):
            return valid
            
    return name_str.strip()  # Return original stripped if unresolved


# ==============================================================================
# ANOMALY DETECTION ENGINE
# ==============================================================================
def run_anomaly_detection(csv_rows):
    """
    Why this exists:
    Reads all rows from the parsed CSV, performs check-by-check validations,
    and returns a structured report of valid rows and anomalies with their severity and actions.
    
    Returns:
      dict: {
        'total_rows': int,
        'valid_records': list of dicts,
        'anomalies': list of dicts (with row_number, severity, anomaly_type, action_taken, row_data)
      }
    """
    report = {
        'total_rows': len(csv_rows),
        'valid_records': [],
        'anomalies': []
      }
      
    # List to store successfully processed rows to perform duplicate scans within the same sheet
    processed_history = []

    for index, raw_row in enumerate(csv_rows):
        row_num = index + 2  # Row 1 is the header, index starts at 0, so row number = index + 2
        
        # Prepare clean fields dict to modify/auto-correct values
        clean_row = {
            'row_number': row_num,
            'original_date': raw_row.get('date', ''),
            'original_description': raw_row.get('description', ''),
            'original_paid_by': raw_row.get('paid_by', ''),
            'original_amount': raw_row.get('amount', ''),
            'original_currency': raw_row.get('currency', ''),
            'original_split_type': raw_row.get('split_type', ''),
            'original_split_with': raw_row.get('split_with', ''),
            'original_split_details': raw_row.get('split_details', ''),
            'original_notes': raw_row.get('notes', ''),
            
            # Placeholders for parsed/cleaned values
            'date': None,
            'description': '',
            'paid_by': '',
            'amount': Decimal('0.00'),
            'currency': 'INR',
            'exchange_rate': Decimal('1.00'),
            'split_type': 'equal',
            'split_with': [],
            'split_details': {},
            'notes': '',
            'is_settlement': False,
            'is_refund': False,
            'action_summary': []
        }

        row_errors = []
        row_warnings = []
        row_infos = []

        # ----------------------------------------------------------------------
        # 1. VALIDATE & PARSE DATE
        # ----------------------------------------------------------------------
        raw_date = raw_row.get('date', '').strip()
        parsed_date = parse_dirty_date(raw_date)
        
        if not raw_date:
            row_errors.append({
                'type': 'Missing Date',
                'desc': 'Date field is empty.'
            })
        elif not parsed_date:
            row_errors.append({
                'type': 'Invalid Date Format',
                'desc': f"Unable to parse date: '{raw_date}'"
            })
        else:
            clean_row['date'] = parsed_date
            # Check if date is in the future
            if parsed_date > datetime.date.today():
                row_warnings.append({
                    'type': 'Future Date',
                    'desc': f"Expense date '{parsed_date}' is in the future."
                })
            # Check if date format was cleaned (e.g. Mar 14 or DD/MM/YYYY)
            if '/' in raw_date or '-' not in raw_date:
                row_infos.append({
                    'type': 'Date Format Cleaned',
                    'desc': f"Inconsistent date format '{raw_date}' parsed to standard '{parsed_date}'"
                })

        # ----------------------------------------------------------------------
        # 2. VALIDATE & PARSE TITLE (DESCRIPTION)
        # ----------------------------------------------------------------------
        title = raw_row.get('description', '').strip()
        if not title:
            row_warnings.append({
                'type': 'Blank Title',
                'desc': 'Description is blank. Auto-assigning "Untitled Expense".'
            })
            clean_row['description'] = 'Untitled Expense'
        else:
            clean_row['description'] = title

        # ----------------------------------------------------------------------
        # 3. VALIDATE & PARSE AMOUNT
        # ----------------------------------------------------------------------
        raw_amount = raw_row.get('amount', '').strip()
        # Remove quotes and commas (e.g. "1,200" -> 1200)
        clean_amount_str = raw_amount.replace('"', '').replace(',', '').strip()
        
        amount_val = Decimal('0.00')
        if not raw_amount:
            row_errors.append({
                'type': 'Missing Amount',
                'desc': 'Amount is empty.'
            })
        else:
            try:
                amount_val = Decimal(clean_amount_str)
                clean_row['amount'] = amount_val
                
                # Check for decimals rounding (e.g. 899.995)
                if '.' in clean_amount_str and len(clean_amount_str.split('.')[1]) > 2:
                    rounded = round(amount_val, 2)
                    row_infos.append({
                        'type': 'Precision Decimal Rounded',
                        'desc': f"Amount {amount_val} rounded to 2 decimal places: {rounded}"
                    })
                    clean_row['amount'] = rounded
                    
                # Negative amount check (Refund vs Error)
                if amount_val < 0:
                    clean_row['is_refund'] = True
                    row_infos.append({
                        'type': 'Negative Amount Detected',
                        'desc': f"Negative amount {amount_val} processed as a Refund."
                    })
                elif amount_val == 0:
                    row_warnings.append({
                        'type': 'Zero Amount',
                        'desc': 'Amount is zero. This is logged but split is empty.'
                    })
            except (ValueError, InvalidOperation):
                row_errors.append({
                    'type': 'Invalid Amount Value',
                    'desc': f"Cannot parse amount '{raw_amount}' as a number."
                })

        # ----------------------------------------------------------------------
        # 4. VALIDATE & PARSE CURRENCY
        # ----------------------------------------------------------------------
        raw_currency = raw_row.get('currency', '').strip()
        if not raw_currency:
            row_infos.append({
                'type': 'Missing Currency Defaulted',
                'desc': 'Currency is missing. Defaulted to INR.'
            })
            clean_row['currency'] = 'INR'
            clean_row['exchange_rate'] = Decimal('1.000000')
        elif raw_currency.upper() not in ['INR', 'USD']:
            row_errors.append({
                'type': 'Unsupported Currency',
                'desc': f"Unsupported currency '{raw_currency}'. Supported currencies are INR, USD."
            })
        else:
            currency_upper = raw_currency.upper()
            clean_row['currency'] = currency_upper
            if currency_upper == 'USD':
                clean_row['exchange_rate'] = FIXED_USD_TO_INR_RATE
                row_infos.append({
                    'type': 'USD Currency Exchange Applied',
                    'desc': f"USD detected. Applied fixed exchange rate of {FIXED_USD_TO_INR_RATE} INR."
                })
            else:
                clean_row['exchange_rate'] = Decimal('1.00')

        # ----------------------------------------------------------------------
        # 5. VALIDATE & PARSE PAYER (PAID BY)
        # ----------------------------------------------------------------------
        raw_payer = raw_row.get('paid_by', '').strip()
        cleaned_payer = clean_username(raw_payer)
        
        if not raw_payer:
            row_errors.append({
                'type': 'Missing Payer',
                'desc': 'The payer field is empty.'
            })
        elif cleaned_payer not in VALID_USERS:
            row_errors.append({
                'type': 'Unknown Payer',
                'desc': f"Payer '{raw_payer}' is not registered in the system."
            })
        else:
            clean_row['paid_by'] = cleaned_payer
            if cleaned_payer != raw_payer:
                row_infos.append({
                    'type': 'Payer Name Cleaned',
                    'desc': f"Auto-corrected payer spelling from '{raw_payer}' to '{cleaned_payer}'"
                })

        # ----------------------------------------------------------------------
        # 6. IDENTIFY IF SETTLEMENT LOGGED AS EXPENSE
        # ----------------------------------------------------------------------
        desc_lower = clean_row['description'].lower()
        split_type_raw = raw_row.get('split_type', '').strip().lower()
        
        # Heuristics:
        # - Split type is empty AND notes/description mentions "paid back", "deposit", "settled"
        # - Or description explicitly says "paid back"
        is_settlement_detected = False
        if not split_type_raw and raw_row.get('split_with', ''):
            is_settlement_detected = True
        elif 'paid back' in desc_lower or 'deposit share' in desc_lower or 'settled' in desc_lower:
            is_settlement_detected = True
            
        if is_settlement_detected and cleaned_payer in VALID_USERS:
            clean_row['is_settlement'] = True
            clean_row['split_type'] = 'settlement'
            # The settlement recipient is parsed from split_with or split_details
            raw_split_with = raw_row.get('split_with', '').strip()
            clean_recipient = clean_username(raw_split_with)
            
            if clean_recipient in VALID_USERS:
                clean_row['split_with'] = [clean_recipient]
                row_infos.append({
                    'type': 'Settlement Detected',
                    'desc': f"Detected payment settlement: {cleaned_payer} paid {clean_recipient} directly."
                })
            else:
                row_errors.append({
                    'type': 'Invalid Settlement Recipient',
                    'desc': f"Recipient '{raw_split_with}' for settlement is invalid or missing."
                })

        # ----------------------------------------------------------------------
        # 7. PARSE SPLIT MEMBERS (SPLIT WITH)
        # ----------------------------------------------------------------------
        if not clean_row['is_settlement']:
            raw_split_with = raw_row.get('split_with', '').strip()
            split_members = []
            
            if not raw_split_with:
                row_errors.append({
                    'type': 'Missing Split Members',
                    'desc': 'split_with list is empty.'
                })
            else:
                # Remove quotes and split by semi-colon
                raw_split_with = raw_split_with.replace('"', '')
                raw_list = [m.strip() for m in raw_split_with.split(';') if m.strip()]
                
                for m in raw_list:
                    cleaned_m = clean_username(m)
                    if cleaned_m in VALID_USERS:
                        split_members.append(cleaned_m)
                        if cleaned_m != m:
                            row_infos.append({
                                'type': 'Split Member Name Cleaned',
                                'desc': f"Auto-corrected split member name from '{m}' to '{cleaned_m}'"
                            })
                    else:
                        row_warnings.append({
                            'type': 'Unknown Split Member Ignored',
                            'desc': f"Member '{m}' in split is unknown. Excluded from calculation."
                        })
                
                clean_row['split_with'] = split_members

        # ----------------------------------------------------------------------
        # 8. VALIDATE ACTIVE MEMBERSHIP DATES (Sam & Meera checks)
        # ----------------------------------------------------------------------
        # Only check if dates and names are parsed
        if clean_row['date'] and clean_row['paid_by'] in VALID_USERS:
            expense_date = clean_row['date']
            
            # Check Payer active status
            payer_dates = MEMBERSHIP_DATES[clean_row['paid_by']]
            if payer_dates['joined'] > expense_date:
                row_errors.append({
                    'type': 'Payer Not Joined Yet',
                    'desc': f"Payer {clean_row['paid_by']} had not joined the flat on {expense_date}."
                })
            elif payer_dates['left'] and payer_dates['left'] < expense_date:
                row_errors.append({
                    'type': 'Payer Already Left',
                    'desc': f"Payer {clean_row['paid_by']} had already left the flat on {expense_date}."
                })
                
            # Check Split Members active status
            inactive_members = []
            for member in clean_row['split_with']:
                m_dates = MEMBERSHIP_DATES[member]
                if m_dates['joined'] > expense_date:
                    inactive_members.append(member)
                    row_warnings.append({
                        'type': 'Member Joined After Expense Date',
                        'desc': f"Member {member} joined on {m_dates['joined']} but expense is on {expense_date}."
                    })
                elif m_dates['left'] and m_dates['left'] < expense_date:
                    inactive_members.append(member)
                    row_warnings.append({
                        'type': 'Member Left Before Expense Date',
                        'desc': f"Member {member} left on {m_dates['left']} but expense is on {expense_date}."
                    })
            
            # Action Taken: Remove inactive members from split list
            if inactive_members:
                clean_row['split_with'] = [m for m in clean_row['split_with'] if m not in inactive_members]
                row_infos.append({
                    'type': 'Inactive Members Excluded',
                    'desc': f"Excluded inactive members {inactive_members} from splitting on date {expense_date}."
                })

        # ----------------------------------------------------------------------
        # 9. VALIDATE SPLIT RATIO/DETAILS (EQUAL, PERCENTAGE, SHARE, UNEQUAL)
        # ----------------------------------------------------------------------
        if not clean_row['is_settlement'] and clean_row['split_with'] and not row_errors:
            split_type = raw_row.get('split_type', '').strip().lower()
            raw_details = raw_row.get('split_details', '').strip()
            
            # Map 'unequal' to 'exact'
            if split_type == 'unequal':
                split_type = 'exact'
            elif not split_type:
                split_type = 'equal'  # Default
                
            clean_row['split_type'] = split_type
            
            # Split details dictionary will hold individual shares/amounts
            split_details = {}
            total_members = len(clean_row['split_with'])
            total_amount = clean_row['amount']

            # Case A: EQUAL Split
            if split_type == 'equal':
                equal_share = total_amount / total_members
                for member in clean_row['split_with']:
                    split_details[member] = equal_share

            # Case B: EXACT / UNEQUAL Split
            elif split_type == 'exact':
                # Parse: Rohan 700; Priya 400; Meera 400
                raw_details_clean = raw_details.replace('"', '')
                tokens = [t.strip() for t in raw_details_clean.split(';') if t.strip()]
                parsed_sum = Decimal('0.00')
                
                for token in tokens:
                    match = re.match(r'^(.+)\s+([\d\.\-]+)$', token)
                    if match:
                        name_raw = match.group(1).strip()
                        amount_str = match.group(2).strip()
                        name_clean = clean_username(name_raw)
                        
                        if name_clean in clean_row['split_with']:
                            try:
                                val = Decimal(amount_str)
                                split_details[name_clean] = val
                                parsed_sum += val
                            except InvalidOperation:
                                pass
                                
                # Check for split sum mismatch
                if abs(parsed_sum - total_amount) > Decimal('0.01'):
                    row_errors.append({
                        'type': 'Split Amount Sum Mismatch',
                        'desc': f"Sum of exact splits ({parsed_sum}) does not match total amount ({total_amount})."
                    })
                else:
                    # Fill missing split members with 0
                    for member in clean_row['split_with']:
                        if member not in split_details:
                            split_details[member] = Decimal('0.00')

            # Case C: PERCENTAGE Split
            elif split_type == 'percentage':
                # Parse: Aisha 30%; Rohan 30%; Priya 30%; Meera 20%
                raw_details_clean = raw_details.replace('"', '').replace('%', '')
                tokens = [t.strip() for t in raw_details_clean.split(';') if t.strip()]
                parsed_percentage_sum = Decimal('0.00')
                
                for token in tokens:
                    match = re.match(r'^(.+)\s+([\d\.\-]+)$', token)
                    if match:
                        name_raw = match.group(1).strip()
                        pct_str = match.group(2).strip()
                        name_clean = clean_username(name_raw)
                        
                        if name_clean in clean_row['split_with']:
                            try:
                                pct = Decimal(pct_str)
                                split_details[name_clean] = (pct / Decimal('100')) * total_amount
                                parsed_percentage_sum += pct
                            except InvalidOperation:
                                pass
                                
                # Check if total percentage sum is 100%
                if abs(parsed_percentage_sum - Decimal('100')) > Decimal('0.01'):
                    row_errors.append({
                        'type': 'Split Percentage Sum Mismatch',
                        'desc': f"Sum of percentages ({parsed_percentage_sum}%) does not equal 100%."
                    })
                else:
                    for member in clean_row['split_with']:
                        if member not in split_details:
                            split_details[member] = Decimal('0.00')

            # Case D: SHARE Split (Ratios)
            elif split_type == 'share':
                # Parse: Aisha 1; Rohan 2; Priya 1; Dev 2
                raw_details_clean = raw_details.replace('"', '')
                tokens = [t.strip() for t in raw_details_clean.split(';') if t.strip()]
                shares_dict = {}
                total_shares = Decimal('0.00')
                
                for token in tokens:
                    match = re.match(r'^(.+)\s+(\d+)$', token)
                    if match:
                        name_raw = match.group(1).strip()
                        share_str = match.group(2).strip()
                        name_clean = clean_username(name_raw)
                        
                        if name_clean in clean_row['split_with']:
                            try:
                                val = Decimal(share_str)
                                shares_dict[name_clean] = val
                                total_shares += val
                            except InvalidOperation:
                                pass
                                
                if total_shares == 0:
                    row_errors.append({
                        'type': 'Invalid Shares Sum',
                        'desc': 'Total shares sum is zero.'
                    })
                else:
                    for member in clean_row['split_with']:
                        member_share = shares_dict.get(member, Decimal('0'))
                        split_details[member] = (member_share / total_shares) * total_amount
                        
            clean_row['split_details'] = split_details

        # ----------------------------------------------------------------------
        # 10. DUPLICATES SCAN (Meera's Request - Review workflow)
        # ----------------------------------------------------------------------
        # We compare this row against already processed rows in this run to detect duplicates
        is_duplicate = False
        is_conflict = False
        duplicate_ref = None

        if clean_row['date'] and clean_row['paid_by'] in VALID_USERS and not row_errors:
            for past in processed_history:
                # Rule for Exact Duplicate: Same date, paid_by, amount, split list, and very similar description
                if (past['date'] == clean_row['date'] and 
                    past['paid_by'] == clean_row['paid_by'] and 
                    abs(past['amount'] - clean_row['amount']) < Decimal('0.01') and
                    sorted(past['split_with']) == sorted(clean_row['split_with'])):
                    
                    is_duplicate = True
                    duplicate_ref = past['row_number']
                    break
                
                # Rule for Conflict Duplicate (Row 24 Dinner at Thalassa by Aisha 2400 vs Row 25 Rohan 2450)
                # Same date, similar description keywords, same split participants, different payers or amounts
                if (past['date'] == clean_row['date'] and 
                    sorted(past['split_with']) == sorted(clean_row['split_with'])):
                    
                    word1 = set(past['description'].lower().replace('dinner', '').replace('at', '').split())
                    word2 = set(clean_row['description'].lower().replace('dinner', '').replace('at', '').split())
                    
                    # If description overlaps, flag as potential duplicate conflict
                    if word1.intersection(word2) or 'thalassa' in past['description'].lower() and 'thalassa' in clean_row['description'].lower():
                        is_conflict = True
                        duplicate_ref = past['row_number']
                        break

            if is_duplicate:
                row_warnings.append({
                    'type': 'Duplicate Expense Row',
                    'desc': f"Exact duplicate of row #{duplicate_ref} detected. Logged for review."
                })
            elif is_conflict:
                row_warnings.append({
                    'type': 'Potential Duplicate Conflict',
                    'desc': f"Possible duplicate overlap with row #{duplicate_ref} (e.g. same day/meal, different details)."
                })

        # ----------------------------------------------------------------------
        # 11. RECORD STATUS & DECIDE ACTION
        # ----------------------------------------------------------------------
        if row_errors:
            # Errors MUST block auto-import. Status = rejected.
            severity = 'error'
            action = f"Rejected: {'; '.join([e['desc'] for e in row_errors])}"
            status = 'rejected'
            anomaly_type = row_errors[0]['type']
        elif row_warnings:
            # Warnings need user review but can be imported after approval
            severity = 'warning'
            action = f"Flagged for Review: {'; '.join([w['desc'] for w in row_warnings])}"
            status = 'pending_review'
            anomaly_type = row_warnings[0]['type']
        else:
            # Info only or totally clean. Import immediately.
            severity = 'info'
            action = "Auto-imported"
            status = 'approved'
            anomaly_type = 'None'
            if row_infos:
                action += f" (Note: {'; '.join([i['desc'] for i in row_infos])})"
                anomaly_type = row_infos[0]['type']

        # Store full action summary on clean_row
        clean_row['action_summary'] = {
            'row_number': row_num,
            'anomaly_type': anomaly_type,
            'severity': severity,
            'action_taken': action,
            'status': status
        }

        # Save to report lists
        if status == 'approved':
            report['valid_records'].append(clean_row)
            processed_history.append(clean_row)
        else:
            # Even if pending_review or rejected, we record it in anomalies list
            report['anomalies'].append({
                'row_number': row_num,
                'anomaly_type': anomaly_type,
                'severity': severity,
                'action_taken': action,
                'status': status,
                'row_data': raw_row  # Keep original data for db storage
            })
            
            # If it's pending_review (like warnings), we STILL want to allow saving it as a pending record
            if status == 'pending_review':
                # Add to processed history so later duplicates can still find it
                processed_history.append(clean_row)

    return report
