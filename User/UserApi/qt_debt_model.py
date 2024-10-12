from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
from sqlalchemy import and_, text, func, desc, update
from typing import List, Dict, Any
from datetime import datetime
import re
import os, sys


DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from User.UserApi.database import get_db
from User.UserApi.models import (
    HandLoans,
    TransactionsPast,
    FreedomFuture,
    AccountsPresent,
)

app = FastAPI(title="QT Debt API", version="1.0.0")
app_qt_debt = APIRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/swagger", include_in_schema=False)
async def get_open_api_endpoint():
    return get_openapi(title="QT Debt API", version="1.0.0", routes=app.routes)


@app.get("/docs", include_in_schema=False)
async def get_documentation():
    return get_swagger_ui_html(openapi_url="/swagger", title="QT Debt API")


@app_qt_debt.get("/")
def read_root():
    return {"message": "Welcome to the QT Debt API"}


def query_hand_loans(db: Session) -> List[Dict[str, Any]]:
    hand_loans = (
        db.query(HandLoans)
        .filter(and_(HandLoans.AccID.like("HL%"), ~HandLoans.AccID.like("HLG%")))
        .all()
    )
    return [loan.__dict__ for loan in hand_loans]


@app_qt_debt.get("/hand_loans")
def read_hand_loans(db: Session = Depends(get_db)):
    try:
        result = query_hand_loans(db)
        print(f"Number of hand loans fetched: {len(result)}")
        return {"hand_loans": result}
    except Exception as e:
        print(f"Error in read_hand_loans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app_qt_debt.get("/transactions")
def read_transactions(db: Session = Depends(get_db)):
    try:
        transactions = db.query(TransactionsPast).all()
        result = [
            {
                "TrNo": transaction.TrNo,
                "Date": transaction.Date,
                "Description": transaction.Description,
                "Amount": transaction.Amount,
                "PaymentMode": transaction.PaymentMode,
                "AccID": transaction.AccID,
                "Department": transaction.Department,
                "Comments": transaction.Comments,
                "Category": transaction.Category,
                "DeductedReceivedThrough": transaction.DeductedReceivedThrough,
                "ZohoMatch": transaction.ZohoMatch,
                "ExpectedPaymentDate": transaction.ExpectedPaymentDate,
            }
            for transaction in transactions
        ]
        print(f"Number of transactions fetched: {len(result)}")
        return {"transactions": result}
    except Exception as e:
        print(f"Error in read_transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app_qt_debt.get("/freedom_future")
def read_freedom_future(db: Session = Depends(get_db)):
    try:
        freedom_future_records = (
            db.query(FreedomFuture)
            .filter(
                and_(FreedomFuture.AccID.like("HL%"), ~FreedomFuture.AccID.like("HLG%"))
            )
            .all()
        )
        result = [
            {
                "TrNo": freedom_future_record.TrNo,
                "Date": freedom_future_record.Date,
                "Description": freedom_future_record.Description,
                "Amount": freedom_future_record.Amount,
                "PaymentMode": freedom_future_record.PaymentMode,
                "AccID": freedom_future_record.AccID,
                "Department": freedom_future_record.Department,
            }
            for freedom_future_record in freedom_future_records
        ]
        print(f"Number of Freedom Future records fetched: {len(result)}")
        return {"freedom_future": result}
    except Exception as e:
        print(f"Error in read_freedom_future: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app_qt_debt.get("/combined_loans")
def read_combined_loans(db: Session = Depends(get_db)):
    try:
        freedom_future_records = (
            db.query(FreedomFuture)
            .filter(
                and_(FreedomFuture.AccID.like("HL%"), ~FreedomFuture.AccID.like("HLG%"))
            )
            .all()
        )

        # Group records by AccID
        grouped_records = {}
        for record in freedom_future_records:
            if record.AccID not in grouped_records:
                grouped_records[record.AccID] = []
            grouped_records[record.AccID].append(record)

        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        result = []
        for accID, records in grouped_records.items():
            print(f"Processing AccID: {accID}")

            # Find the upcoming month record
            upcoming_month_record = None
            for ff_record in records:
                match = re.search(r"(\d{4})\s+(\w+)\s+Interest", ff_record.Description)
                if match:
                    year = int(match.group(1))
                    month = datetime.strptime(match.group(2), "%B").month
                    if (year > current_year) or (
                        year == current_year and month > current_month
                    ):
                        if upcoming_month_record is None or (year, month) < (
                            upcoming_month_record.year,
                            upcoming_month_record.month,
                        ):
                            upcoming_month_record = ff_record
                            upcoming_month_record.year = year
                            upcoming_month_record.month = month

            # Use upcoming month record or fall back to the first record
            record_to_use = upcoming_month_record or records[0]

            # Fetch balance from HandLoans
            hand_loan = (
                db.query(HandLoans)
                .filter(HandLoans.AccID == accID)
                .order_by(desc(HandLoans.Date))
                .first()
            )

            if hand_loan:
                balance = hand_loan.Balance
                interest = balance * 0.0133
                interest_earned = round(interest, 2)
                name = hand_loan.Name
            else:
                balance = 0
                interest_earned = 0
                name = "Unknown"

            combined_record = {
                "AccID": accID,
                "Date": record_to_use.Date,
                "Description": record_to_use.Description,
                "Amount": record_to_use.Amount,
                "PaymentMode": record_to_use.PaymentMode,
                "Department": record_to_use.Department,
                "Balance": balance,
                "Interest": interest_earned,
                "Name": name,
            }
            # print(f"Combined record: {combined_record}")
            result.append(combined_record)

        # Insert new transactions into TransactionsPast
        for record in result:
            # Generate a new TrNo
            max_tr_no = db.query(func.max(TransactionsPast.TrNo)).scalar() or 0
            new_tr_no = max_tr_no + 1

            new_transaction = TransactionsPast(
                TrNo=new_tr_no,
                Date=record["Date"],
                Description=record["Description"],
                Amount=record["Interest"],
                PaymentMode=record["PaymentMode"],
                AccID=record["AccID"],
                Department=record["Department"],
                Comments=None,
                Category="Hand Loans",
                DeductedReceivedThrough=None,
                ExpectedPaymentDate=None,
            )
            db.add(new_transaction)
            # Create new HandLoans entry
            handloan_tr_no = db.query(func.max(HandLoans.TrNo)).scalar() or 0
            new_handloan_tr_no = handloan_tr_no + 1
            total_balance = round(
                float(record["Balance"]) + float(record["Interest"]), 2
            )

            new_hand_loan = HandLoans(
                TrNo=new_handloan_tr_no,
                Date=record["Date"],
                Description=record["Description"],
                Amount=int(record["Interest"]),
                AccID=record["AccID"],
                Department=record["Department"],
                Comments=None,
                Name=record["Name"],
                Balance=total_balance,
            )
            db.add(new_hand_loan)

            # Update AccountsPresent table with the new total balance
            update_stmt = (
                update(AccountsPresent)
                .where(AccountsPresent.AccID == record["AccID"])
                .values(CurrentBalance=total_balance)
            )
            db.execute(update_stmt)

            db.flush()

        db.commit()

        print(f"Number of combined records: {len(result)}")
        return {"combined_loans": result}
    except Exception as e:
        db.rollback()
        print(f"Error in read_combined_loans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


app.include_router(app_qt_debt, prefix="/qt_debt")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)
