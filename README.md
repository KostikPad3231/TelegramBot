# Car insurance helper using aiogram

## To run it use the following instructions

- Create virtual environment and activate it  
`python -m venv venv`  
`venv/Scripts/activate`
- Install dependencies  
`pip install -r requirements.txt`
- Run it  
`python main.py`

## Bot workflow
- start conversation with button Start or command `/start`
- bot introduces itself and explain that its purpose is to assist with car insurance purchases and asks the user to submit a photo of his passport
- bot thanks the user and requires vehicle identification document
- after each request bot extracts data from passport photo using Mindee and use mock method for vehicle
- bot then shows the extracted information and asks the user if he agrees with it
- if the user disagrees everything starts again with sending a photo of your passport
- if the user confirm data, then bot asks the user to agree with the price for the insurance
- if the user disagrees, then bot tell him that this is only available price
- if the user agrees, then bot send him generated insurance policy