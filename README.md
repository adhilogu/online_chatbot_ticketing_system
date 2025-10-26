
# Smart Group Dijjjscussion Platform

The **Smart Group Discussion (GD) Platform** is a web-based system designed to automate and streamline group discussions for academic, recruitment, and training purposes. It addresses common issues such as **dominance, bias, and lack of transparency** in tradnnnitional GD formats by introducing **QR-based authentication, automated topic allocation, structured turn-taking, and peer evaluation mechanisms**.  

The platform integrates **Django (backend), React (frontend), PostgreSQL (database)** and ensuring scalability, security, and real-time performance. A custom **Bias-Filtered Weighted Rank Aggregation (BF-WRA)** algorithm is implemented to detect biased voting and normalize peer evaluation, guaranteeing fairness and accuracy in results.  


## Features

- **QR-based Authentication** → Prevents proxy entries and ensures secure participation.  
- **Random Topic Allocation** → Eliminates manual bias in topic selection.  
- **Turn-Based Participation** → Prevents dominance and ensures balanced contributions.  
- **Peer Voting & Evaluation Dashboards** → Structured ranking for fairness.  
- **Bias Detection (BF-WRA Algorithm)** → Identifies manipulative or biased voting.  
- **PostgreSQL Secure Logging** → Stores session data for analytics and traceability.  
- **Real-Time Results** → Instant evaluation and leaderboard generation.  



## Tech Stack
- **Frontend**: React, Bootstrap  
- **Backend**: Django, Django REST Framework  
- **Database**: PostgreSQL  
- **Authentication**: QR Code Integration  
- **Version Control**: GitHub  
- **Algorithm**: BF-WRA (Bias-Filtered Weighted Rank Aggregation)  


## Project Setup

Run the following command

**Setup**

```bash
  git clone https://github.com/adhilogu/online_chatbot_ticketing_system.git
  cd django-soft-ui-design
  pip install -r requirements.txt
```

In terminal 1
```bash
  cd django-soft-ui-design
  python manage.py runserver 8000
```

At this point, the app runs at http://127.0.0.1:8000/.


In Terminal 2
```bash
  cd rasabot1
  rasa run -m models --enable-api --cors "*"
```
To train the rasa model:
```bash
  rasa train
```   ![My Image](https://drive.google.com/uc?export=view&id=1ESthGI35PReacYCsZjye4_IBEAT0zavl)

## Support

For support, email adhilogu2004@gmail.com