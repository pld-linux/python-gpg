%define		module	gpg
Summary:	A Python module for the the gpg
Summary(pl):	Modu³ Pythona do gpg
Name:		python-%{module}
# it's cvs revision number
Version:	1.3
Release:	1
License:	GPL
Group:		Libraries/Python
# http://cvs.sourceforge.net/viewcvs.py/pycrypto/gpg/GPG.py
Source0:	GPG.py
# Source0-md5:	a665162fdd1a485ad6c5ac2551e12d0e
URL:		http://www.python.org/moin/GnuPrivacyGuard
BuildRequires:	rpm-pythonprov
Requires:	python-modules
BuildArch:	noarch
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
GnuPG interface for Python.

%description -l pl
Interfejs do GnuPG dla Python.

%prep
%setup -q -c -T

%install
rm -rf $RPM_BUILD_ROOT
install -d $RPM_BUILD_ROOT%{py_sitedir}

install %{SOURCE0} $RPM_BUILD_ROOT%{py_sitedir}

%py_comp $RPM_BUILD_ROOT%{py_sitedir}
%py_ocomp $RPM_BUILD_ROOT%{py_sitedir}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(644,root,root,755)
%{py_sitedir}/*.py?
