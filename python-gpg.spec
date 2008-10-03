%define		module	gpg
Summary:	A Python module for the GnuPG
Summary(pl.UTF-8):	Moduł Pythona do GnuPG
Name:		python-%{module}
# it's cvs revision number
Version:	1.3
Release:	4
License:	GPL
Group:		Libraries/Python
# http://cvs.sourceforge.net/viewcvs.py/pycrypto/gpg/GPG.py
Source0:	GPG.py
# NoSource0-md5:	a665162fdd1a485ad6c5ac2551e12d0e
URL:		http://www.python.org/moin/GnuPrivacyGuard
%pyrequires_eq	python-modules
BuildArch:	noarch
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
GnuPG interface for Python.

%description -l pl.UTF-8
Interfejs do GnuPG dla Pythona.

%prep
%setup -q -c -T

%install
rm -rf $RPM_BUILD_ROOT
install -d $RPM_BUILD_ROOT%{py_sitescriptdir}
install %{SOURCE0} $RPM_BUILD_ROOT%{py_sitescriptdir}
%py_comp $RPM_BUILD_ROOT%{py_sitescriptdir}
%py_ocomp $RPM_BUILD_ROOT%{py_sitescriptdir}
%py_postclean

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(644,root,root,755)
%{py_sitescriptdir}/*.py[co]
