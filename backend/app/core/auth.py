# app/core/auth.py
from jose import jwt, JWTError
from fastapi import HTTPException
import traceback
from app.core.config import settings

def verify_clerk_token(token: str) -> str:
    """
    Verifies a Clerk JWT token and returns the user's ID (the 'sub' claim).
    """
    try:
        # Use the Public Key from Clerk stored in your .env/settings
        payload = jwt.decode(
            token,
            settings.CLERK_JWT_PUBLIC_KEY,
            algorithms=["RS256"],
            # If you haven't configured these in Clerk yet, 
            # you can comment these two lines out temporarily to test.
            audience=settings.CLERK_JWT_AUDIENCE,
            issuer=settings.CLERK_ISSUER
        )
        
        user_id = payload.get("sub")
        if not user_id:
            print("AUTH ERROR: Token payload missing 'sub' claim.")
            raise HTTPException(status_code=401, detail="Token missing subject")
            
        return user_id

    except JWTError as e:
        print(f"JWT VERIFICATION ERROR: {str(e)}")
        # This usually means the Public Key is wrong or the token is expired
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")
    except Exception as e:
        print(f"CRITICAL AUTH ERROR: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=401, detail="Could not validate credentials")