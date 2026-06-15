package impl

object Main extends App {

  private def germanyPlayers =
    List(Defender("Kimmich", 6), Defender("Rüdiger", 2), Defender("Tah", 4), Defender("Mittelstädt", 18),
      Midfielder("Andrich", 23), Midfielder("Kroos", 8), Midfielder("Gündoğan", 21),
      Midfielder("Musiala", 10), Forward("Havertz", 7), Forward("Wirtz", 17), Goalkeeper("Neuer", 1))

  private def scotlandPlayers =
    List(Defender("Tierney", 6), Defender("Porteous", 15), Defender("Hendry", 13),
      Defender("Robertson", 3), Midfielder("McGregor", 8), Midfielder("McTominay", 4), Defender("Ralston", 2),
      Forward("Christie", 11), Forward("Adams", 10), Midfielder("McGinn", 7), Goalkeeper("Gunn", 1))

  private def germanyVsScotlandEvents = List(
    FirstHalf,
    Goal(10, "Wirtz"),
    Goal(19, "Musiala"),
    YellowCard(31, "Andrich"),
    RedCard(44, "Porteous"),
    Goal(46, "Havertz"),
    HalfTime(48),
    SecondHalf,
    Substitution(
      minute = 46,
      playerIn = Midfielder("Gross", 5),
      nameOut = "Andrich"
    ),
    Substitution(
      minute = 46,
      playerIn = Defender("Hanley", 5),
      nameOut = "Adams"
    ),
    YellowCard(48, "Ralston"),
    YellowCard(62, "Tah"),
    Substitution(
      minute = 63,
      playerIn = Midfielder("Sané", 19),
      nameOut = "Wirtz"
    ),
    Substitution(
      minute = 63,
      playerIn = Forward("Füllkrug", 9),
      nameOut = "Havertz"
    ),
    Substitution(
      minute = 67,
      playerIn = Forward("Gilmour", 14),
      nameOut = "McGregor"
    ),
    Substitution(
      minute = 67,
      playerIn = Forward("McLean", 23),
      nameOut = "McGinn"
    ),
    Goal(68, "Füllkrug"),
    Substitution(
      minute = 74,
      playerIn = Forward("Müller", 13),
      nameOut = "Musiala"
    ),
    Substitution(
      minute = 77,
      playerIn = Defender("McKenna", 26),
      nameOut = "Tierney"
    ),
    Substitution(
      minute = 80,
      playerIn = Midfielder("Can", 25),
      nameOut = "Kroos"
    ),
    Substitution(
      minute = 77,
      playerIn = Forward("Shankland", 9),
      nameOut = "Christie"
    ),
    OwnGoal(87, "Rüdiger"),
    Goal(93, "Can"),
    GameOver(93)
  )

  private val gerVsScot: FootballMatch = {
    FootballMatch(
      Team("Deutschland", germanyPlayers),
      Team("Schottland", scotlandPlayers)
    )
  }


  germanyVsScotlandEvents.foreach(gerVsScot.handleEvent(_))

  println("-" * 80)

  println("Das Spiel läuft " + (if (gerVsScot.isRunning) "noch" else "nicht mehr"))
  println("Das Spiel ist " + (if (gerVsScot.isOver) "" else "nicht ") + "vorbei!")
  println("Spielzeit: " + gerVsScot.totalTime + " Minuten")
  println("Endstand: " + gerVsScot.score1 + " - " + gerVsScot.score2)
  println("Deutsche Spieler am Ende des Spiels auf dem Feld: " + gerVsScot.playersTeam1.map(_.name).mkString(", "))
  println("Schottische Spieler am Ende des Spiels auf dem Feld: " + gerVsScot.playersTeam2.map(_.name).mkString(", "))

  //println("Deutschland hat " + (if (FootballMatch.didGermanyWin(gerVsScot)) "gewonnen" else "nicht gewonnen"))
}
