# from fastapi import FastAPI, File, UploadFile, HTTPException
# import pandas as pd
# from io import StringIO
# import smtplib
# import validators
# import dns.resolver
# from fastapi.middleware.cors import CORSMiddleware
# import asyncio
# from fastapi.responses import JSONResponse
# import os
# app = FastAPI()

# origins = [
#     # "https://email-validation-fr.vercel.app"
#     # "https://email-val.netlify.app/"
#     # "https://email-validation-90.pages.dev"
#     "http://localhost:3000"
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,           # Allows the frontend origin
#     allow_credentials=True,          # Allows cookies or credentials
#     allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Allowed HTTP methods
#     allow_headers=["Content-Type", "Authorization"],  # Allowed headers
# )

# mx_cache = {}

# def check_mx_records(domain): 
#     if domain in mx_cache:
#         return mx_cache[domain]

#     try:
#         records = dns.resolver.resolve(domain, 'MX')
#         for record in records:
#             mx_cache[domain] = str(record.exchange)
#             return mx_cache[domain]
#     except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout, dns.resolver.NoNameservers):
#         mx_cache[domain] = None
#         return None

# def verify_email_sync(email):
#     check_validate = validators.email(email)
#     if not check_validate:
#         return {"email": email, "is_valid": False}
    
#     domain_split = email.split('@')[-1]
#     email_not_valid = email.split('@')[0]
#     email_not_valid_2=email.split('.')[-1]
#     if email_not_valid_2 in ["edu","gov","org",]:
#         return {"email": email, "is_valid": False}
#     if email_not_valid in ["helpdesk","volunteers","office","customer","customercare","privacy","enquiry","inquiry","order","info","mail","admin","supportteam","notice","partner","partnership","services","service","commercial","webmaster","postmaste","hola","post","welcome","example","invoice","advise","admission","communication","ventas","kontakt","contacto","client","terms","donate","promo","promotion","project","feedback","hr","sample","online","function","member","membership","reception","reservation","support","account","hello","career","resume","recovery","whois","domain","proxy","registration","admin","shop","hi","demo","template","hosting","assistenza","atendimento","commerciale","generalinfo","subscribe","noreply","support","contact","payment","payroll","abuse","billing","submission","spam","write","emails"]:
#           return {"email": email, "is_valid": False}
#     if domain_split in ["gmail.com","yahoo.com","hotmail.com","outlook.com","aol.com","abc.com","xyz.com","godaddy.com","email.com"]:
#          return {"email": email, "is_valid": False}
#     mx_host = check_mx_records(domain_split)
#     if not mx_host:
#         return {"email": email, "is_valid": False}
    
#     try:
#         server = smtplib.SMTP(mx_host)
#         server.set_debuglevel(0)
#         server.helo()
#         server.mail("hk6488808@gmail.com")
#         code, _ = server.rcpt(email)
#         server.quit()
#         return {"email": email, "is_valid": code == 250}
#     except:
#         return {"email": email, "is_valid": False}

# async def verify_email(email):
#     loop = asyncio.get_event_loop()
#     return await loop.run_in_executor(None, verify_email_sync, email)

# @app.post("/message")
# async def main(file: UploadFile = File(...)):
#     try:
#         contents = await file.read()
#         df = pd.read_csv(StringIO(contents.decode('utf-8')))
        
#         if 'email' not in df.columns:
#             raise HTTPException(status_code=400, detail="CSV file must contain 'email' column")

#         emails = df['email'].tolist()
#         batch_size = 6 
#         results = []
#         for i in range(0, len(emails), batch_size):
#             batch = emails[i:i+batch_size]
#             tasks = [verify_email(email) for email in batch]
#             results = await asyncio.gather(*tasks)
#             results.extend(results)
#             # df['is_valid'] = [result['is_valid'] for result in results]
            
            
#         df[ 'is_valid'] = [result['is_valid'] for result in results]

        
       
#         # tasks = [verify_email(email) for email in emails]
#         # results = await asyncio.gather(*tasks)
        
      
#         # df['is_valid'] = [result['is_valid'] for result in results]
        
#         return df.to_dict(orient="records")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     import uvicorn
#     port = int(os.environ.get("PORT", 8000))
#     uvicorn.run(app, host="0.0.0.0", port=port)

from fastapi import FastAPI, File, UploadFile, HTTPException
import logging
import pandas as pd
from io import StringIO
import smtplib
import validators
import dns.resolver
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from fastapi.responses import JSONResponse
import os
import redis.asyncio as aioredis
from aiosmtplib import SMTP
from concurrent.futures import ThreadPoolExecutor
app = FastAPI()

origins = [
    # "https://email-validation-fr.vercel.app"
    # "https://email-val.netlify.app/"
    # "https://email-validation-90.pages.dev"
    "http://52.66.255.242"
]
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          
    allow_credentials=True,        
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  
    allow_headers=["Content-Type", "Authorization"], 
)
mx_cache = {}
semaphore = asyncio.Semaphore(50) 


async def check_mx_records(domain,timeout=10):
   
    
    if domain in mx_cache:
        return mx_cache[domain]
    try:
        records = dns.resolver.resolve(domain, 'MX')
        for record in records:
            mx_host = str(record.exchange)
            mx_cache[domain] = mx_host
           
            return mx_host
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout, dns.resolver.NoNameservers):
        mx_cache[domain] = None
        return None

async def verify_email_sync(email):
    check_validate = validators.email(email)
    if not check_validate:
        logger.debug(f"Email validation failed: {email}")
        return {"email": email, "is_valid": False}

    domain_split = email.split('@')[-1]
    email_not_valid = email.split('@')[0]
    email_not_valid_2 = email.split('.')[-1]
    
    if email_not_valid_2 in ["edu", "gov", "org"]:
        return {"email": email, "is_valid": False}
    
    if email_not_valid in ["helpdesk", "volunteers", "office", "customer", "customercare", "privacy", "enquiry", "inquiry", "order", "info", "mail", "admin", "supportteam", "notice", "partner", "partnership", "services", "service", "commercial", "webmaster", "postmaste", "hola", "post", "welcome", "example", "invoice", "advise", "admission", "communication", "ventas", "kontakt", "contacto", "client", "terms", "donate", "promo", "promotion", "project", "feedback", "hr", "sample", "online", "function", "member", "membership", "reception", "reservation", "support", "account", "hello", "career", "resume", "recovery", "whois", "domain", "proxy", "registration", "admin", "shop", "hi", "demo", "template", "hosting", "assistenza", "atendimento", "commerciale", "generalinfo", "subscribe", "noreply", "support", "contact", "payment", "payroll", "abuse", "billing", "submission", "spam", "write", "emails"]:
        return {"email": email, "is_valid": False}
    
    if domain_split in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "abc.com", "xyz.com", "godaddy.com", "email.com"]:
        return {"email": email, "is_valid": False}
    
    mx_host = await check_mx_records(domain_split)
    if not mx_host:
        logger.debug(f"MX host not found for {email}")
        return {"email": email, "is_valid": False}
       

    try:
        async with SMTP(hostname=mx_host,port=587) as server:
            await asyncio.wait_for(server.connect(), timeout=60)
            await server.helo()
            await server.mail("hk6488808@gmail.com")
            code, _ = await asyncio.wait_for(server.rcpt(email), timeout=60)
            logger.debug(f"SMTP RCPT code: {code} for {email}")
            return {"email": email, "is_valid": code == 250}
    except Exception as e:
        logger.error(f"SMTP verification failed for {email}, error: {str(e)}")
        return {"email": email, "is_valid": False}

executor = ThreadPoolExecutor(max_workers=20)
async def verify_email(email):
    return await verify_email_sync(email)

@app.post("/message")
async def main(file: UploadFile = File(...)):
    try:
        logger.info("received file")
        contents = await file.read()
        df = pd.read_csv(StringIO(contents.decode('utf-8')))
        
        logger.debug(f"CSV contents: {df.head()}")
        if 'email' not in df.columns:
            raise HTTPException(status_code=400, detail="CSV file must contain 'email' column")

        emails = df['email'].tolist()
        logger.info(f"Validating emails: {emails}")
        batch_size = 25
        results = []

        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            logger.info(f"Processing batch: {batch}")
            tasks = [verify_email(email) for email in batch]
            batch_results = await asyncio.gather(*tasks) 
            results.extend(batch_results)
            logger.info(results) 

        df['is_valid'] = [result['is_valid'] for result in results]  
        logger.info("Validation completed successfully")
        
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
 
 
