# Configs for Fusion Directory Service and Selenium WebDriver - Chrome Driver

Fusion_Directory_URL ='$URL'

credentials = {
'MFA_SECRET' : '',  # Find MFA Secret Key while scanning QR code while setting up 2FA in myCloud and enter the Secret Key here - https://mycloud.pearson.com/Mfa
'USERNAME' : '',  # myCloud ID
'PASSWORD' : ''  # myCloud Password
}

chromeDriver = {
    'BIN_LOCATION': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # Hardcoded For Mac - change for other platforms
    'EXEC_PATH': ''  # Path where you have downloaded chrome driver - http://chromedriver.chromium.org/downloads
}
