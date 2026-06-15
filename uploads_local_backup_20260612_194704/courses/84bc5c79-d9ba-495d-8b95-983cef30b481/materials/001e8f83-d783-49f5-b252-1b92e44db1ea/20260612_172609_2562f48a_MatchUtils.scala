package impl

/** A player with a name and a role */
sealed trait Player {
  def name: String
  def number: Int
  var yellowCards: Int = 0
}

case class Goalkeeper(name: String, number: Int) extends Player
case class Defender(name: String, number: Int) extends Player
case class Midfielder(name: String, number: Int) extends Player
case class Forward(name: String, number: Int) extends Player

/** A team with a name and a set of players */
case class Team[P](name: String, players: List[P])