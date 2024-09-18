from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
from sqlalchemy import and_, inspect
from datetime import datetime
import uvicorn

from database import get_db
from models import HandLoans, TransactionsPast, FreedomFuture

app = FastAPI()  # Create the main FastAPI app
app_qt_debt = APIRouter()  # Create the router

# Add CORS middleware to the main app
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


@app_qt_debt.get("/hand_loans")
def read_hand_loans(db: Session = Depends(get_db)):
    try:
        hand_loans = (
            db.query(HandLoans)
            .filter(and_(HandLoans.accID.like("HL%"), ~HandLoans.accID.like("HLG%")))
            .all()
        )
        print(f"Number of hand loans fetched: {len(hand_loans)}")

        result = []
        for loan in hand_loans:
            loan_dict = {
                column.key: getattr(loan, column.key)
                for column in inspect(loan).mapper.column_attrs
            }
            result.append(loan_dict)

        return {"hand_loans": result}
    except Exception as e:
        print(f"Error in read_hand_loans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app_qt_debt.get("/transactions")
def read_transactions(db: Session = Depends(get_db)):
    try:
        transactions = db.query(TransactionsPast).all()
        print(f"Number of transactions fetched: {len(transactions)}")

        result = []
        for transaction in transactions:
            transaction_dict = {
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
            result.append(transaction_dict)

        return {"transactions": result}
    except Exception as e:
        print(f"Error in read_transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app_qt_debt.get("/freedom_future")
def read_freedom_future(db: Session = Depends(get_db)):
    try:
        # Query all records from the FreedomFuture table
        freedom_future_records = (
            db.query(FreedomFuture)
            .filter(
                and_(FreedomFuture.AccID.like("HL%"), ~FreedomFuture.AccID.like("HLG%"))
            )
            .all()
        )

        print(
            f"Number of Freedom Future records fetched: {len(freedom_future_records)}"
        )

        result = []
        for record in freedom_future_records:
            record_dict = {
                "TrNo": record.TrNo,
                "Date": record.Date,
                "Description": record.Description,
                "Amount": record.Amount,
                "PaymentMode": record.PaymentMode,
                "AccID": record.AccID,
                "Department": record.Department,
            }
            result.append(record_dict)

        return {"freedom_future": result}
    except Exception as e:
        print(f"Error in read_freedom_future: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app_qt_debt.get("/combined_loans")
def read_combined_loans(db: Session = Depends(get_db)):
    try:
        # Fetch accounts from FreedomFuture
        freedom_future_records = (
            db.query(FreedomFuture)
            .filter(
                and_(FreedomFuture.AccID.like("HL%"), ~FreedomFuture.AccID.like("HLG%"))
            )
            .all()
        )

        result = []
        for record in freedom_future_records:
            # Fetch balance from HandLoans for each account
            hand_loan = (
                db.query(HandLoans).filter(HandLoans.accID == record.AccID).first()
            )

            if hand_loan:
                balance = hand_loan.Balance
                interest = balance * 1.33
                interest_earned = interest - balance
            else:
                balance = 0
                interest = 0
                interest_earned = 0

            combined_record = {
                "AccID": record.AccID,
                "Date": record.Date,
                "Description": record.Description,
                "Amount": record.Amount,
                "PaymentMode": record.PaymentMode,
                "Department": record.Department,
                "Balance": balance,
                "Interest": interest_earned,
            }
            result.append(combined_record)

        print(f"Number of combined records: {len(result)}")
        return {"combined_loans": result}
    except Exception as e:
        print(f"Error in read_combined_loans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Include the router in the main app
app.include_router(app_qt_debt, prefix="/qt_debt")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
