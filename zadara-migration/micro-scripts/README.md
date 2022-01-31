1. Clone the repo 
`git clone https://bitbucket.pearson.com/scm/~uumarar/zadara-find.git`
2. Change permissions for get-zadara-usage script
`chmod +x get-zadara-usage.sh`

3. Configure the aws credentials
`aws configure`

4. Run the script with VPC id.
`./get-zadara-usage.sh <VPC_ID>`
