# Rapport de livraison — EDR (option A, sans AWS)

## Objet
Service générique de récupération asynchrone de données automobiles simulées, avec API REST, IAM, orchestration Step Functions et stockage DynamoDB.

## Solution fournie
- Trois opérations API : POST /requests ; GET /requests/{requestId} ; GET /requests/{requestId}/result.
- Définition Terraform des ressources AWS et des politiques IAM associées.
- State machine ASL avec validation, autorisation, fournisseur simulé, stockage et gestion d'échecs.
- Stratégie anti-throttling : rate limit configurable au niveau API, attente dynamique Retry-After simulé pour 429, retries exponentiels limités pour erreurs temporaires.
- Tests unitaires Python exécutables localement et documentation complète.

## Positionnement de la remise
Cette livraison est une **proposition technique hors déploiement**. Elle ne démontre pas une exécution réelle sur AWS. Terraform fmt/validate/plan doivent être exécutés par le candidat et leur sortie ajoutée au rapport avant remise. `terraform apply` n'est pas requis par le sujet.

## Choix et compromis
- API Gateway REST + AWS_IAM : SigV4 plutôt que secrets statiques. Autorisation applicative par liste d'opérations et contrôle de propriété par identité IAM. Une autorisation fine et multi-utilisateurs nécessiterait une source d'habilitations dédiée.
- Step Functions Standard : exécutions asynchrones et gestion explicite des retries. Pour un Retry-After réel, convertir et plafonner les valeurs HTTP avant attente.
- DynamoDB on-demand : status et résultats de petite taille, sans serveur. Les grands objets devraient aller dans S3.
- Mock fournisseur : aucune donnée réelle et aucun token nécessaire ; une ressource Secrets Manager vide illustre la séparation entre métadonnées et contenu sensible.
- Aucune VPC dédiée nécessaire à ce mock. Connexion à un fournisseur privé : architecture réseau supplémentaire à prévoir.

## Procédure de validation
Depuis la racine : `python -m unittest discover -s tests -v`.
Depuis `terraform/` : `terraform init -backend=false`, `terraform fmt -recursive`, `terraform validate`, `terraform plan -refresh=false -var-file=environments/dev.tfvars`.

## Limites à annoncer à l'oral
- Vérification des interactions AWS et validation de la state machine par AWS non exécutées.
- Tests unitaires et contrôle de structure ASL, pas de tests E2E cloud.
- L'identité propriétaire IAM doit être repensée si les utilisateurs passent par les mêmes rôles assumés.
- Aucun secret ne doit être initialisé dans le state Terraform ; il faut injecter les valeurs par processus sécurisé hors Terraform.
