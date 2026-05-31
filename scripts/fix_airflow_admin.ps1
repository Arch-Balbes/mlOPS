# Set Airflow login to admin / admin
$container = "infra-airflow-1"
docker exec $container airflow users delete -u admin 2>$null
docker exec $container airflow users create -u admin -p admin --firstname Admin --lastname User -r Admin -e admin@example.com
Write-Host "Done. Login: admin / admin at http://localhost:8080"
