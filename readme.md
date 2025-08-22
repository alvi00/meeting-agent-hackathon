

source meeting_venv/bin/activate

python manage.py migrate   
python manage.py start_scheduler
python manage.py runserver

GCS_BUCKET_NAME="meeting-bucket-alvi123" python manage.py runserver


wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin
