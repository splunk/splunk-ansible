SSH_KEY_DIR = '../ssh_public_keys'
$file = 'C:\ProgramData\ssh\sshd_config'
$find = '#PasswordAuthentication yes'
$replace = 'PasswordAuthentication no'
(Get-Content $file).replace($find, $replace) | Set-Content $file
$find = '#StrictModes yes'
$replace = 'StrictModes no'
(Get-Content $file).replace($find, $replace) | Set-Content $file
# Setup accounts
mkdir C:\Users\Administrator\.ssh
New-Item -ItemType file -Path C:\Users\Administrator\.ssh\authorized_keys
for keyfile in `ls $SSH_KEY_DIR/*.pub`; do
    USERNAME=`echo $keyfile | sed -e 's,.*/\([a-zA-Z0-9]*\).pub$,\1,'`
    Write-Host "Adding $USERNAME keys..."
    Add-Content "C:\Users\Administrator\.ssh\authorized_keys" "`cat $keyfile`"
\$authorizedKeyPath = "C:\Users\Administrator\.ssh\authorized_keys"
\$acl = Get-Acl \$authorizedKeyPath
\$ar = New-Object System.Security.AccessControl.FileSystemAccessRule("NT Service\sshd", "Read", "Allow")
\$acl.SetAccessRule(\$ar)
Set-Acl \$authorizedKeyPath \$acl