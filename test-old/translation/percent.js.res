function wrapper(){alert("Hallo Welt");
alert("Kurz");
alert("Danke für die Blumen");
alert("Guten Morgen");
alert("Guten Morgen! Morgen!");
alert("Guten "+this.computeGreeting()+"! "+this.computeGreeting()+"!");
alert("Unterhaltung");
alert("Chat Online");
alert("Chat "+this.getChatStatus());
alert(newMails<=1?"Sie haben eine neue Mail":"Sie haben neue Mails");
alert(newMails<=1?"Sie haben eine neue Mail":"You have got "+(newMails+1)+" new mails")}
