$(function() {
	"use strict";
	
	/*var location = document.location.href;
	var url = new URL( location );
	var close = url.searchParams.get( 'c' );

	function empty( value ) {
		return (value === null || value.length === 0);
	}

	if ( empty( close ) ) {
		
		var sys = window.open( (url + '?c=0'), 'Consultas', 'fullscreen=yes, directories = ' + 0 + ', titlebar = ' + 0 + ', toolbar = ' + 0 + ', location = ' + 0 + ', status = ' + 0 + ', menubar = ' + 0 + ', scrollbars = no, resizable = no, width = ' + screen.availWidth + ', height= ' + screen.availHeight );
		
		if ( sys === null || typeof(sys) === 'undefined' ) {
			$('ul.flex-container').remove().append(function() {
				$('<style type="text/css">#popupMsg{text-align:center;text-transform:uppercase;font-size:35pt;font-weight:lighter;color:#fff;font-family:PRIMETIME,sans-serif;text-shadow:1px 1px 3px rgba(0,0,0,.7)}#popupMsg>a{font-size:20pt;color:#ffa651}#reload{margin:30px;padding:15px 30px;text-transform:uppercase;font-weight:700;color:#464646}</style><h2 id="popupMsg">Permita pop-ups para essa página. <br />Aprenda mais em <br /><a href="https://support.google.com/chrome/answer/95472?co=GENIE.Platform%3DDesktop&hl=pt-BR" target="_blank">Permitir pop-ups no Chrome</a></h2><button id="reload">Recarregar Página</button>').prependTo('body');
			});
		} 
		else {
			$('html').html('');
			sys.focus();
		}
		

	} else { 

		$('ul.flex-container').load('./menu.html');
		var newUrl = location.split('?')[ 0 ];
		window.history.pushState( {}, document.title, newUrl );

	}*/
	
	$('ul.flex-container').load('./menu.html');
	
	$(document).contextmenu(function(e) {
		e.preventDefault();
	});
	
	$(document).keydown(function(e) {
		if ( e.keyCode === 123 ) {
			return false;
		} else if ( e.ctrlKey && e.shiftKey && e.keyCode === 73 ) { 
			return false;
		}
	});
	
	$(document).on('click', '#reload', function() {
		window.document.location.reload(true);
	});
	
});