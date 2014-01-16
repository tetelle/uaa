"""
error_reporting(-1);
ini_set('display_errors',1);
$request_body = file_get_contents('php://input');
$xml = simplexml_load_string($request_body);

switch($xml->methodName)
{
	//wordpress blog verification
	case 'mt.supportedMethods':
		success('metaWeblog.getRecentPosts');
		break;
	//first authentication request from ifttt
	case 'metaWeblog.getRecentPosts':
		//send a blank blog response
		//this also makes sure that the channel is never triggered
		success('<array><data></data></array>');
		break;

	case 'metaWeblog.newPost':
		//@see http://codex.wordpress.org/XML-RPC_WordPress_API/Posts#wp.newPost
		$obj = new stdClass;
		//get the parameters from xml
		$obj->user = (string)$xml->params->param[1]->value->string;
		$obj->pass = (string)$xml->params->param[2]->value->string;

        // Update the local date-time in a file somewhere
        date_default_timezone_set("UTC");
        $now = new DateTime(null, new DateTimeZone('UTC'));
        file_put_contents("/tmp/last_update.txt", $now->format('c'));

        success('<string>200</string>');
}
"""
# Copied from wordpress 

def success(innerXML):
  pass
  """
	$xml =  <<<EOD
<?xml version="1.0"?>
<methodResponse>
  <params>
    <param>
      <value>
      $innerXML
      </value>
    </param>
  </params>
</methodResponse>
EOD;
	output($xml);
}"""

def output(xml):
  pass
  """
	$length = strlen($xml);
	header('Connection: close');
	header('Content-Length: '.$length);
	header('Content-Type: text/xml');
	header('Date: '.date('r'));
	echo $xml;
	exit;
  """

def failure(status):
  pass
  """
$xml= <<<EOD
<?xml version="1.0"?>
<methodResponse>
  <fault>
    <value>
      <struct>
        <member>
          <name>faultCode</name>
          <value><int>$status</int></value>
        </member>
        <member>
          <name>faultString</name>
          <value><string>Request was not successful.</string></value>
        </member>
      </struct>
    </value>
  </fault>
</methodResponse>
EOD;
output($xml);
"""

# Used from drupal 
def valid_url(url, absolute = FALSE) :
  pass
  """
  if ($absolute) {
    return (bool) preg_match("
      /^                                                      # Start at the beginning of the text
      (?:https?):\/\/                                # Look for ftp, http, https or feed schemes
      (?:                                                     # Userinfo (optional) which is typically
        (?:(?:[\w\.\-\+!$&'\(\)*\+,;=]|%[0-9a-f]{2})+:)*      # a username or a username and password
        (?:[\w\.\-\+%!$&'\(\)*\+,;=]|%[0-9a-f]{2})+@          # combination
      )?
      (?:
        (?:[a-z0-9\-\.]|%[0-9a-f]{2})+                        # A domain name or a IPv4 address
        |(?:\[(?:[0-9a-f]{0,4}:)*(?:[0-9a-f]{0,4})\])         # or a well formed IPv6 address
      )
      (?::[0-9]+)?                                            # Server port number (optional)
      (?:[\/|\?]
        (?:[\w#!:\.\?\+=&@$'~*,;\/\(\)\[\]\-]|%[0-9a-f]{2})   # The path and query (optional)
      *)?
    $/xi", $url);
  }
  else {
    return (bool) preg_match("/^(?:[\w#!:\.\?\+=&@$'~*,;\/\(\)\[\]\-]|%[0-9a-f]{2})+$/i", $url);
  }


