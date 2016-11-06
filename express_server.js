/*
 * Author: reddyv@
 * Last Updated: 11-05-2016
 * Usage: node express_server.js
 * ToDo:
 *  1) 
 *
*/

//Load required modules
var express = require('express') //npm module: web framework
var multer = require('multer') //https://www.npmjs.com/package/multer

//Initialize
var express = express()
var upload = multer()

//Define routes
express.get('/', function (req, res) {
	res.sendFile(__dirname + '/html/form.html') 
	//__dirname is a nodejs global representing the current directory
})

express.post('/', upload.array(), function (req, res) {
  res.send(req.body.question)
})

//Start the server
var server = express.listen('8080', function () {
  console.log('Server listening on port %s', server.address().port)
})
