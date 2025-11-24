# Package Manager
package managers suck
they all work basically the same
and have the same problems
not enough apps
half my apps aren't availible
and it's so so annoying to have to install 20 different package managers just to get my favorite apps
How do we solve this?
We don't!
Because the problem is developers
Users love package managers
they keep everything organized in one place
but developers hate them
too many rules
to little flexibility
and it's really hard to make profitable closed source software
when the damn app store wants a cut
So we fixed it
We took the stuff developers love about distrobuting apps on windows
and the stuff users love about installing apps on linux
and made EpsilonOS
Users get the peace of mind knowing there apps are contained
even if you install malware the permission system prevents apps from going haywire
apps are sandboxed
and their files are contained
their dependentcies are contained
and when you uninstall all traces are gone
forever
Thats great
but develpers hate permission systems
they make coding a pain in the ass
so we kept it simple
instead of a million tini permissions there are a few more broud access rights
and some stuff is just given by default like a temp and data folder access to ram and cpu
We also made it harder for users to spoof permissions or read app data
So devs can keep their intelectual property safe
But how do users know apps are trustworthy
Well we could take the Microsoft route of having a complex and broken digital signature system
or we could take the linux route of proof reading each and every app added to the repository
but both of those suck
see we already have a system for trusted brand identity
its the https and domain system
everyone knows google.com is trustworthy and g00gle.hacks is not
and the https CAs are really really good
so we just steal there work and make use of it
every domain can host a file at google.com/sigkey.pub and any apps signed with that key are trusted
This is great cause it puts app developers in control of what they sign
and they can easily sign subkeys and then revoke those subkeys at any time by updating their sigkey.pub file
now thats awesome
this also lets apps host their own install files
app package files can be downloaded from the internet from any website you want
EpsilonOS will warn you if the app is unsigned or if the website seems sus (aka a known malware domain or a newly registered domain or a domain that looks like a typo)
but mostly its up to develpers and users to handle software
EpsilonOS stays out of the way
It's as convinient as windows but also more secure

# SCS and Sheilded Popups
Down in the bottom left corner of the screen when a SCS (secure consent screen) is showing
you will see a sheild icon. This icon indicates that the popup is a legitimate system popup
and more specifically indicates that secure input mode has been enabled. When secure input mode
is active all inputs coming from programs that lack the (send high integrity input) permission are immediately
discarded. This means all calls to SendVirtualInput will silently fail and any buffered virtual inputs
will immediately be discarded. Additionally the operating system always has full control over the display
and will usually take exclusive control over all displays when in secure input mode.
If the user at any point feels unsafe or worries that their screen have malware they can press Ctrl + Alt + Delete
this keystroke sequence is always handled by the operating system and results in the following actions:
1. Secure input is enabled and the shield icon is displayed
2. All connected monitors are exclusively controlled by the operating system and go to the recovery tty

# SCS Permission Popups
If an app needs access to a restricted resource they can ask the user.
For example an app can say Hi I need access to your camera. Can has plz?

# SCS File Open Popups
Having to hit yes or no on a million permission popups is annoying.
And users don't always know which files they want to open in each app.
If I download an image editor I don't know which images I will want to edit or which folders they will be in.
So most users in this sitation will just hit allow access to all files.
But thats bad because it means any program which needs access to any file can access things like browser cookies or sensitive documents.
A better idea is to use SCS file open popups
With these an app can say file>open and then when the user selects an image it automatically gives the image editor access to that file for the duration of this execution session.
That makes it super duper easy for an app to access any file it needs but not easy to access sensive data.

# SCS App Server
App (my app) wants to host a server on port 8080
allow? yes no

# LuksBuks
Stands for Linus Unified Key System + Buckets
This is a modification of the Luks filesystem which adds support for buckets
Each bucket has a name which acts as a unique identifier.

# Multiple users?
Yes you can have multiple users.
Each user gets their own home folder.
Nobody can touch each others home folder.
Each user gets the illusion of having their own apps just for them.
In reality though the read only part of the apps code is shared between users.

# App Folders
Per App Folders:
$bin = /apps/f6e015d2-bdbc-4fb3-bc0d-2fb452a42742/bin ro
$data = /apps/f6e015d2-bdbc-4fb3-bc0d-2fb452a42742/data rw
$tmp = /tmp/f6e015d2-bdbc-4fb3-bc0d-2fb452a42742/ rw ramfs

Shared Folders

# Permission Higharchy
When one process starts another some permissions are passed down and others aren't depending on certain factors.
Each process has two permission contexts self and caller_given
By default we assume the parent trusts the child but that the child doesn't trust the parent.
As such the child is launched with all the permissions in caller_given and none of the permissions in self.
Additionally caller_given contains all the permissions that the parent has by default.
If the parent would like to modify caller_given to not give so much permissions it can do so by specifying a list of perms to give or a list of perms not to give.
The child will by default have access to only the permissions in caller_given.
If the child needs more they can call ElevateContext() or ResetContext() to optionally enable or disable the permissions in self.
Setuid Binaries:
Binaries with the setuid bit set to true have different default behavior. They have ElevateContext() automatically called on launch before main() in invoked.
This however does not prevent setuid binaries from calling ResetContext() if they don't need these extra permissions for greater security.
Restricted Contexts:
A process can also call restrict context at any time and pass a list of permissions to remove or a list of permissions which should be the only ones not removed.
This places the process in a restricted context which applies until the next call to ResetContext()
This allows processes which require higher levels of permission to temporarily drop those permissions for greater security.
This can come in particularly handy if you need to do something sketchy like read data off the network or run user scripts.
Additional note a parent which is temporarily in a restricted context will pass on that restricted context to children. Not the full parent permissions.