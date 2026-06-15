package impl

/**
 * Represents a football game
 *
 * @param team1 team number one
 * @param team2 team number two
 */
class FootballMatch(team1: Team[Player], team2: Team[Player]) {
  var score1 = 0 // score of team 1
  var score2 = 0 // score of team 2
  var totalTime = 0 // total running time of the game
  var isRunning = false // is the game currently running?
  var isOver = false // is the game over?

  // team names and players on the team
  var Team(teamName1, playersTeam1) = team1
  var Team(teamName2, playersTeam2) = team2

  private def log(msg: String, minute: Int) : Unit = {
    println(s"""[$teamName1 gegen $teamName2 ($minute)]: $msg""")
  }

  override def toString = s"$teamName1 $score1 : $score2 $teamName2"

  println(s"Willkommen zum Spiel: $teamName1 gegen $teamName2")
  println("-" * 80)

  //TODO: implement handleEvent
  def handleEvent(event: Event) : Unit = event match {
    // time-related events

    // goal-related events

    // card-related events

    // substitution events

    // default
    case _ => // do nothing
  }
}

object FootballMatch {

  def apply(team1: Team[Player], team2: Team[Player]) = new FootballMatch(team1, team2)

  //TODO: implement unapply method

  //TODO: implement after unapply

}

