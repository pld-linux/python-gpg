'''
Code for running GnuPG from Python and dealing with the results.

Detailed info about the format of data to/from gpg may be obtained from the
file DETAILS in the gnupg source.
'''

__rcsid__ = '$Id$'

import os, StringIO, popen2

class Signature:
    "Used to hold information about a signature result"

    def __init__(self):
        self.valid = 0
        self.fingerprint = self.creation_date = self.timestamp = None
        self.signature_id = self.key_id = None
        self.username = None

    def BADSIG(self, value):
        self.valid = 0
        self.key_id, self.username = value.split(None, 1)
    def GOODSIG(self, value):
        self.valid = 1
        self.key_id, self.username = value.split(None, 1)
    def VALIDSIG(self, value):
        self.fingerprint, self.creation_date, self.timestamp = value.split()
    def SIG_ID(self, value):
        self.signature_id, self.creation_date, self.timestamp = value.split()

    def is_valid(self):
        return self.valid
 
class ImportResult:
    "Used to hold information about a key import result"

    counts = '''count no_user_id imported imported_rsa unchanged
            n_uids n_subk n_sigs n_revoc sec_read sec_imported
            sec_dups not_imported'''.split()
    def __init__(self):
        self.imported = []
        self.results = []
        for result in self.counts:
            setattr(self, result, None)
    
    def NODATA(self, value):
        self.results.append({'fingerprint': None,
            'problem': '0', 'text': 'No valid data found'})
    def IMPORTED(self, value):
        # this duplicates info we already see in import_ok and import_problem
        pass
    ok_reason = {
        '0': 'Not actually changed',
        '1': 'Entirely new key',
        '2': 'New user IDs',
        '4': 'New signatures',
        '8': 'New subkeys',
        '16': 'Contains private key',
    }
    def IMPORT_OK(self, value):
        reason, fingerprint = value.split()
        self.results.append({'fingerprint': fingerprint,
            'ok': reason, 'text': self.ok_reason[reason]})
    problem_reason = {
        '0': 'No specific reason given',
        '1': 'Invalid Certificate',
        '2': 'Issuer Certificate missing',
        '3': 'Certificate Chain too long',
        '4': 'Error storing certificate',
    }
    def IMPORT_PROBLEM(self, value):
        try:
            reason, fingerprint = value.split()
        except:
            reason = value
            fingerprint = '<unknown>'
        self.results.append({'fingerprint': fingerprint,
            'problem': reason, 'text': self.problem_reason[reason]})
    def IMPORT_RES(self, value):
        import_res = value.split()
        for i in range(len(self.counts)):
            setattr(self, self.counts[i], int(import_res[i]))

    def summary(self):
        l = []
        l.append('%d imported'%self.imported)
        if self.not_imported:
            l.append('%d not imported'%self.not_imported)
        return ', '.join(l)

class ListResult:
    ''' Parse a --list-keys output

        Handle pub and uid (relating the latter to the former).

        Don't care about (info from src/DETAILS):

        crt = X.509 certificate
        crs = X.509 certificate and private key available
        sub = subkey (secondary key)
        sec = secret key
        ssb = secret subkey (secondary key)
        uat = user attribute (same as user id except for field 10).
        sig = signature
        rev = revocation signature
        fpr = fingerprint: (fingerprint is in field 10)
        pkd = public key data (special field format, see below)
        grp = reserved for gpgsm
        rvk = revocation key
    '''
    def __init__(self):
        self.pub_keys = []
        self.pk = None

    def pub(self, args):
        keyid = args[4]
        date = args[5]
        uid = args[9]
        self.pk = {'keyid': keyid, 'date': date, 'uids': [uid]}
        self.pub_keys.append(self.pk)

    def uid(self, args):
        self.pk['uids'].append(args[9])

class EncryptedMessage:
    ''' Handle a --encrypt command
    '''
    def __init__(self):
        self.data = ''

    def BEGIN_ENCRYPTION(self, value):
        pass
    def END_ENCRYPTION(self, value):
        pass

class DecryptedMessage(object):
    ''' Handle a --decrypt command
    '''
    def __init__(self):
	self.data = ''

    def DECRYPTION_FAILED(self,value):
	raise ValueError, "Decryption failed"

    def empty(self,name):
	pass

    def __getattr__(self,name):
	try:
	    return object.__getattr__(self,name)
	except AttributeError:
	    return self.empty

class GPGSubprocess:

    # Default path used for searching for the GPG binary, when the
    # PATH environment variable isn't set.
    DEFAULT_PATH = ['/bin', '/usr/bin', '/usr/local/bin']
    
    def __init__(self, gpg_binary=None, keyring=None):
        """Initialize an object instance.  Options are:

        gpg_binary -- full pathname for GPG binary.  If not supplied,
        the current value of PATH will be searched, falling back to the
        DEFAULT_PATH class variable if PATH isn't available.

        keyring -- full pathname to the public keyring to use in place of
        the default "~/.gnupg/pubring.gpg".
        """
        # If needed, look for the gpg binary along the path
        if gpg_binary is None:
            if os.environ.has_key('PATH'):
                path = os.environ['PATH']
                path = path.split(os.pathsep)
            else:
                path = self.DEFAULT_PATH

            for dir in path:
                fullname = os.path.join(dir, 'gpg')
                if os.path.exists( fullname ):
                    gpg_binary = fullname
                    break
            else:
                raise ValueError, ("Couldn't find 'gpg' binary on path"
                                   + repr(path) )
            
        self.gpg_binary = gpg_binary
        self.keyring = keyring

    def _open_subprocess(self, *args):
        # Internal method: open a pipe to a GPG subprocess and return
        # the file objects for communicating with it.
        cmd = [self.gpg_binary, '--status-fd 2']
        if self.keyring:
            cmd.append('--keyring "%s" --no-default-keyring'%self.keyring)

        cmd.extend(args)
        cmd = ' '.join(cmd)

        child_stdout, child_stdin, child_stderr = popen2.popen3(cmd)
        return child_stdout, child_stdin, child_stderr

    def _read_response(self, child_stdout, response):
        # Internal method: reads all the output from GPG, taking notice
        # only of lines that begin with the magic [GNUPG:] prefix.
        # 
        # Calls methods on the response object for each valid token found,
        # with the arg being the remainder of the status line.
        while 1:
            line = child_stdout.readline()
            if line == "": break
            line = line.rstrip()
            if line[0:9] == '[GNUPG:] ':
                # Chop off the prefix
                line = line[9:]
                L = line.split(None, 1)
                keyword = L[0]
                if len(L) > 1:
                    value = L[1]
                else:
                    value = ""
                getattr(response, keyword)(value)

    def _handle_gigo(self, args, file, result):
        # Handle a basic data call - pass data to GPG, handle the output
        # including status information. Garbage In, Garbage Out :)
        child_stdout, child_stdin, child_stderr = self._open_subprocess(*args)

        # Copy the file to the GPG subprocess
        while 1:
            data = file.read(1024)
            if data == "": break
            child_stdin.write(data)
        child_stdin.close()

        # Get the response information
        resp = self._read_response(child_stderr, result)

        # Read the contents of the file from GPG's stdout
        result.data = ""
        while 1:
            data = child_stdout.read(1024)
            if data == "": break
            result.data = result.data + data

        return result
    

    #
    # SIGNATURE VERIFICATION METHODS
    #
    def verify(self, data):
        "Verify the signature on the contents of the string 'data'"
        file = StringIO.StringIO(data)
        return self.verify_file(file)
    
    def verify_file(self, file):
        "Verify the signature on the contents of the file-like object 'file'"
        sig = Signature()
        self._handle_gigo([], file, sig)
        return sig

    #
    # KEY MANAGEMENT
    #
    def import_key(self, key_data):
        ''' import the key_data into our keyring '''
        child_stdout, child_stdin, child_stderr = \
            self._open_subprocess('--import')

        child_stdin.write(key_data)
        child_stdin.close()

        # Get the response information
        result = ImportResult()
        resp = self._read_response(child_stderr, result)

        return result

    def list_keys(self):
        ''' list the keys currently in the keyring '''
        child_stdout, child_stdin, child_stderr = \
            self._open_subprocess('--list-keys --with-colons')
        child_stdin.close()

        # TODO: there might be some status thingumy here I should handle...

        # Get the response information
        result = ListResult()
        valid_keywords = 'pub uid'.split()
        while 1:
            line = child_stdout.readline()
            if not line:
                break
            L = line.strip().split(':')
            if not L:
                continue
            keyword = L[0]
            if keyword in valid_keywords:
                getattr(result, keyword)(L)

        return result

    #
    # ENCRYPTING DATA
    #
    def encrypt_file(self, file, recipients):
        "Encrypt the message read from the file-like object 'file'"
        args = ['--encrypt --armor']
        for recipient in recipients:
            args.append('--recipient %s'%recipient)
        result = EncryptedMessage()
        self._handle_gigo(args, file, result)
        return result

    def encrypt(self, data, recipients):
        "Encrypt the message contained in the string 'data'"
        file = StringIO.StringIO(data)
        return self.encrypt_file(file, recipients)


    # Not yet implemented, because I don't need these methods
    # The methods certainly don't have all the parameters they'd need.
    def sign(self, data):
        "Sign the contents of the string 'data'"
        pass

    def sign_file(self, file):
        "Sign the contents of the file-like object 'file'"
        pass

    def decrypt_file(self, file):
        "Decrypt the message read from the file-like object 'file'"
	args = ['--decrypt --armor']
	result = DecryptedMessage()
	self._handle_gigo(args, file, result)
	return result

    def decrypt(self, data):
        "Decrypt the message contained in the string 'data'"
	file = StringIO.StringIO(data)
	return self.decrypt_file(file)
    
if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        print 'Usage: GPG.py <signed file>'
        sys.exit()

    obj = GPGSubprocess()
    file = open(sys.argv[1], 'rb')
    sig = obj.verify_file( file )
    print sig.__dict__
