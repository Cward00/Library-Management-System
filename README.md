# 📚 Library Management System

Library Management System built with Python and SQLite. 

** The system was heavily assisted by AI - Large bulk of code and debugging done with AI **

I used AI to accelerate development, review the architecture of the system and debug complex issues,
reflecting modern development practice 

The System includes:

-CLI interface: User-Friendly and colourful terminal menu using the 'rich' library

-Filtering recommendation engine: Netflix style recommendation engine based on the user's borrowing history

-Full Library Management: Add, search, borrow, return, and delete items


**** HOW TO RUN THE SYSTEM IN TERMINAL ****
1. git clone https://github.com/Cward00/Library-Management-System.git
2. cd Library-Management-System
3. Windows: a. python -m venv venv
            b. venv\Scripts\activate
   Mac/Linux: a. python3 -m venv venv
              b. source venv/bin/activate

   Output: (venv) C:\Users\YourName\Library-Management-System>

4. pip install -r requirements.txt
5. Seed the Database (Optional but Recommended) >> python seed_data.py >> When prompted, type yes and press Enter.
6. python main.py


If you come back to the project later:

cd Library-Management-System

venv\Scripts\activate        # Windows

source venv/bin/activate   # Mac/Linux

python main.py
