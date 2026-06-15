package impl

/** Common sealed supertype for game events */
sealed trait Event {
  val minute: Int
}

/** The game starts (first event) */
case object FirstHalf extends Event {
  val minute = 0
}

/** Half time starts */
case class HalfTime(minute: Int) extends Event

/** Second half starts (always at 45') */
case object SecondHalf extends Event {
  val minute = 45
}

/** the game is over */
case class GameOver(minute: Int) extends Event

/** Goal by a player */
case class Goal(minute: Int, name: String) extends Event

/** Own goal by a player */
case class OwnGoal(minute: Int, name: String) extends Event

/** A player receives a yellow card */
case class YellowCard(minute: Int, name: String) extends Event

/** A player receives a red card */
case class RedCard(minute: Int, name: String) extends Event

/** A player is exchanged for another player */
case class Substitution(minute: Int, playerIn: Player, nameOut: String) extends Event