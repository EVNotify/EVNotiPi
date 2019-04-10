<?php

	echo "Update wird durchgeführt, bitte nicht vom OBD Adapter trennen";
	exec("/var/www/html/PlugAndPlay/runs/update.sh");
?>
	<script type="text/javascript">
	    setTimeout(function() { window.location = "./index.html"; }, 30000);
	</script>
