import requests
from django.conf import settings
from django.shortcuts import redirect , render
from django.http import JsonResponse

from datetime import timedelta
from django.utils.timezone import now
import googleapiclient.discovery
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.http import StreamingHttpResponse, HttpResponse
from google.oauth2.credentials import Credentials
from django.contrib.auth.decorators import login_required
from googleapiclient.discovery import build
from .models import GoogleOAuthToken
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload 
import io
import logging

logger = logging.getLogger(__name__)

def home(request):
    return render( request , "base.html")

def google_login(request):
    
    auth_url = (
        f"{settings.GOOGLE_AUTH_URL}"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid email profile https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/drive.readonly" 
        f"&access_type=offline"
        f"&prompt=consent"
    )

    return redirect(auth_url)

def google_callback(request):
    code = request.GET.get("code")
    if not code: 
        return JsonResponse( { "error"  : "Auth code not found" } , status = 400)
    
    token_data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    token_response = requests.post(settings.GOOGLE_TOKEN_URL , data = token_data )
    token_json = token_response.json()

    # extract access token
    access_token = token_json.get("access_token")
    refresh_token = token_json.get("refresh_token")
    expires_in = token_json.get("expires_in" , 3600)

    try:
        expires_in = int(expires_in)
    except (TypeError, ValueError):
        expires_in = 3600
        
    if not access_token:
        return JsonResponse({"error": "Failed to retrieve access token"}, status=400)

    
    # access token to get user info
    headers = {"Authorization" : f"Bearer {access_token}"}
    user_response = requests.get(settings.GOOGLE_USER_INFO_URL , headers = headers )
    user_data = user_response.json()

    request.session["google_credentials"] = {
        "token": access_token,
        "refresh_token": refresh_token,
        "token_uri": settings.GOOGLE_TOKEN_URL,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
    }

    user, created = User.objects.get_or_create(
        username=user_data['email'], 
        defaults={'first_name': user_data.get('given_name', ''), 'last_name': user_data.get('family_name', '')}
    )

    login(request, user)

    expires_at = now() + timedelta(seconds=expires_in)
    token_type = token_json.get("token_type", "Bearer")

    token_obj, created = GoogleOAuthToken.objects.get_or_create(
        user=user,
        defaults={
            'access_token': access_token,
            'token_type': token_type,
            'expires_at': expires_at,
            'refresh_token': refresh_token
        }
    )

    if not created:
        token_obj.access_token = access_token
        token_obj.token_type = token_type
        token_obj.expires_at = expires_at
        if refresh_token:
            token_obj.refresh_token = refresh_token
        token_obj.save()


    request.session["google_user"] = user_data
    return render(request, 'base.html', { 'user_data': user_data, })

@login_required
def dashboard(request):
    user_data = request.session.get("google_user") 

    if not user_data:
        return redirect("google_login") 

    return render(request, "login.html", {"user_data": user_data})

@login_required
def logout(request):
    request.session.pop("google_credentials", None)
    request.session.pop("google_user", None)
    
    return redirect('home')  

@login_required
def list_drive_files(request):
    
    try:
        token = request.user.drive_token

        if token.is_expired():
            creds = Credentials(
                token.access_token,
                refresh_token=token.refresh_token,
                token_uri=settings.GOOGLE_TOKEN_URL,
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            creds.refresh(googleapiclient.http.Request())
            token.access_token = creds.token
            token.save()

        creds = Credentials(token.access_token)
        drive_service = build("drive", "v3", credentials=creds)

        results = drive_service.files().list(pageSize=10, fields="files(id, name)").execute()
        files = results.get("files", [])

        return render(request, 'drive.html', {'files': files})

    except GoogleOAuthToken.DoesNotExist:
        return HttpResponse("User has not linked their Google Drive account.", status=403)
    except HttpError as e:
        logger.error(f"Google Drive API error in list files: {e}", exc_info=True)
        return HttpResponse(f"Google Drive API error: {e}", status=500)
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        return HttpResponse(f"Error listing files: {str(e)}", status=500)

@login_required
def download_drive_file(request, file_id):
    
    try:
        token = request.user.drive_token

        if token.is_expired():
            creds = Credentials(
                token.access_token,
                refresh_token=token.refresh_token,
                token_uri=settings.GOOGLE_TOKEN_URL,
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            creds.refresh(googleapiclient.http.Request())
            token.access_token = creds.token
            token.save()

        creds = Credentials(token.access_token)
        drive_service = googleapiclient.discovery.build("drive", "v3", credentials=creds)

        file_metadata = drive_service.files().get(fileId=file_id).execute()
        file_name = file_metadata.get("name", "downloaded_file")
        mime_type = file_metadata.get("mimeType", "")

        allowed_mime_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            
        ]

        if mime_type not in allowed_mime_types:
            return HttpResponse(
                "Unsupported file type. Please download and open with an external application.",
                status=400,
            )

        logger.info(f"File ID: {file_id}, Mime Type: {mime_type}") 
        print(f"File ID: {file_id}, Mime Type: {mime_type}")
        print("\n ----------Checkpoint---------- \n")

        export_formats = {
            "application/vnd.google-apps.document": "application/pdf",
            "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.google-apps.presentation": "application/pdf",
        }

        if mime_type in export_formats:
            export_mime = export_formats[mime_type]
            
            try:
                
                request_download = drive_service.files().export_media(fileId=file_id, mimeType=export_mime)
                file_name += ".pdf" if "pdf" in export_mime else ".xlsx"

            except googleapiclient.errors.HttpError as e:
                logger.error(f"Error exporting file: {e}", exc_info=True)
                request_download = drive_service.files().get_media(fileId=file_id)
                export_mime = mime_type 
        else:
            request_download = drive_service.files().get_media(fileId=file_id)
            export_mime = mime_type

        response = StreamingHttpResponse(request_download.execute(), content_type=export_mime)
        print(response)
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'

        return response

    except GoogleOAuthToken.DoesNotExist:
        return HttpResponse("User has not linked their Google Drive account.", status=403)
    except googleapiclient.errors.HttpError as e:
        if e.resp.status == 404:
            return HttpResponse("File not found.", status=404)
        logger.error(f"Google Drive API error: {e}", exc_info=True)
        return HttpResponse(f"Google Drive API error: {e}", status=500)
    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)
        return HttpResponse(f"Error downloading file: {str(e)}", status=500)


@login_required
def upload_file(request):
    try:
        token_obj = GoogleOAuthToken.objects.get(user=request.user)


    except GoogleOAuthToken.DoesNotExist:
        return JsonResponse({"error": "User has not linked their Google Drive account."}, status=403)

    if token_obj.is_expired():
        return JsonResponse({"error": "Google Drive token expired. Please reauthenticate."}, status=401)

    credentials = Credentials(
        token=token_obj.access_token,
        refresh_token=token_obj.refresh_token,
        token_uri=settings.GOOGLE_TOKEN_URL,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive"],
    )

    service = build("drive", "v3", credentials=credentials)

    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]

        file_stream = io.BytesIO(uploaded_file.read())
        media = MediaIoBaseUpload(file_stream, mimetype=uploaded_file.content_type, resumable=True)

        file_metadata = {"name": uploaded_file.name}

        try:
            uploaded_file_data = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
            ).execute()

            file_id = uploaded_file_data.get("id")
        

            return JsonResponse({"message": "File uploaded successfully.", "file_id": file_id, "file_name": uploaded_file.name})
        except Exception as e:
            logger.error(f"Error uploading file: {e}", exc_info=True)
            return JsonResponse({"error": str(e)}, status=500)
        
    return JsonResponse({"error": "No file provided."}, status=400)


