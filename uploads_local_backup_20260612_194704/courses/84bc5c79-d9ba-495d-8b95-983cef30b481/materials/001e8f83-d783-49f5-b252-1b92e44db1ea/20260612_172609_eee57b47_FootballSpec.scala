import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.compiletime.testing.typeChecks
import scala.util.{Try, Success, Failure}
import impl.*
/**
 * Consolidated test suite for the Football project.
 * Includes:
 *  - Covariance check on Team
 *  - Substitution behavior
 *  - Red-card dismissal behavior
 */
class FootballSpec extends AnyFunSuite with Matchers {

  test("Teams of Defenders are a subtype of Teams of Players") {
    assert(
      typeChecks("implicitly[Team[Defender] <:< Team[Player]]"),
      "✗ Team[Defender] is not a subtype of Team[Player]."
    )
  }

  test("FirstHalf starts the game") {
    val dummy = Forward("X", 1)
    val team = Team[Player]("Dummy", List(dummy))
    val fm = new FootballMatch(team, team)

    fm.handleEvent(FirstHalf)

    fm.isRunning shouldBe true
    fm.isOver shouldBe false
    fm.totalTime shouldBe 0
  }

  test("HalfTime stops the game and adds to totalTime") {
    val dummy = Forward("X", 1)
    val team = Team[Player]("Dummy", List(dummy))
    val fm = new FootballMatch(team, team)

    fm.handleEvent(HalfTime(30))

    fm.isRunning shouldBe false
    fm.totalTime shouldBe 30
  }

  test("SecondHalf restarts the game without changing totalTime") {
    val dummy = Forward("X", 1)
    val team = Team[Player]("Dummy", List(dummy))
    val fm = new FootballMatch(team, team)

    fm.handleEvent(SecondHalf)

    fm.isRunning shouldBe true
    fm.totalTime shouldBe 0
  }

  test("GameOver ends the game and finalizes totalTime") {
    val dummy = Forward("X", 1)
    val team = Team[Player]("Dummy", List(dummy))
    val fm = new FootballMatch(team, team)

    // Simulate full game: first half, half time, second half, game over
    fm.handleEvent(FirstHalf)
    fm.handleEvent(HalfTime(46))
    fm.handleEvent(SecondHalf)
    fm.handleEvent(GameOver(92))

    fm.isRunning shouldBe false
    fm.isOver shouldBe true
    fm.totalTime shouldBe 93
  }

  test("Goal for team1 increments score1") {
    val a = Forward("Alice", 10)
    val b = Forward("Bob", 11)
    val team1 = Team[Player]("Team1", List(a))
    val team2 = Team[Player]("Team2", List(b))
    val fm = new FootballMatch(team1, team2)

    fm.handleEvent(Goal(23, "Alice"))
    fm.score1 shouldBe 1
    fm.score2 shouldBe 0
  }

  test("Goal for team2 increments score2") {
    val a = Forward("Alice", 10)
    val b = Forward("Bob", 11)
    val team1 = Team[Player]("Team1", List(a))
    val team2 = Team[Player]("Team2", List(b))
    val fm = new FootballMatch(team1, team2)

    fm.handleEvent(Goal(8, "Bob"))
    fm.score1 shouldBe 0
    fm.score2 shouldBe 1
  }


  test("OwnGoal by team1 increments score2") {
    val a = Forward("Alice", 10)
    val b = Forward("Bob", 11)
    val team1 = Team[Player]("Team1", List(a))
    val team2 = Team[Player]("Team2", List(b))
    val fm = new FootballMatch(team1, team2)

    fm.handleEvent(OwnGoal(15, "Alice"))
    fm.score1 shouldBe 0
    fm.score2 shouldBe 1
  }

  test("OwnGoal by team2 increments score1") {
    val a = Forward("Alice", 10)
    val b = Forward("Bob", 11)
    val team1 = Team[Player]("Team1", List(a))
    val team2 = Team[Player]("Team2", List(b))
    val fm = new FootballMatch(team1, team2)

    fm.handleEvent(OwnGoal(15, "Bob"))
    fm.score2 shouldBe 0
    fm.score1 shouldBe 1
  }


  test("substitution replaces the outgoing player with the incoming one") {
    val p1 = Defender("Alice", 1)
    val team1 = Team[Player]("TestTeam", List(p1, Defender("Bob", 2)))
    val team2 = Team[Player]("Opponent", List(Defender("Dave", 4), Defender("Eve", 5)))
    val fm = new FootballMatch(team1, team2)

    val newPlayer = Defender("Charlie", 3)
    fm.handleEvent(Substitution(15, newPlayer, "Alice"))

    fm.playersTeam1 should contain(newPlayer)
    fm.playersTeam1 should not contain p1
  }

  test("red card triggers dismissal and removal from field") {
    val p1 = Midfielder("Dana", 4)
    val p2 = Midfielder("Eli", 6)
    val team1 = Team[Player]("MidTeam", List(p1, p2))
    val team2 = Team[Player]("OpponentTeam", List(Midfielder("Frank", 8), Midfielder("Grace", 10)))
    val fm = new FootballMatch(team1, team2)

    fm.handleEvent(RedCard(30, "Dana"))
    fm.playersTeam1 should not contain p1
  }

  test("yellow card is recorded") {
    val p1 = Defender("Leo", 1)
    val p2 = Defender("Mia", 3)
    val team1 = Team[Player]("Defenders", List(p1, p2))
    val team2 = Team[Player]("Midfielders", List(Midfielder("Noah", 5), Midfielder("Olivia", 7)))
    val fm = new FootballMatch(team1, team2)

    fm.handleEvent(YellowCard(20, "Mia"))
    fm.playersTeam1.find(_.name == "Mia").map(_.yellowCards) should contain(1)
  }

  test("two yellow cards dismiss player") {
    val p1 = Goalkeeper("Paul", 1)
    val p2 = Goalkeeper("Quinn", 2)
    val team1 = Team[Player]("Goalkeepers", List(p1, p2))
    val team2 = Team[Player]("OpposingGoalkeepers", List(Goalkeeper("Riley", 3), Goalkeeper("Sam", 4)))
    val fm = new FootballMatch(team1, team2)
    fm.handleEvent(YellowCard(25, "Paul"))
    fm.handleEvent(YellowCard(30, "Paul"))

    fm.playersTeam1 should not contain p1
  }

  test("unapply returns games result (if implemented)") {
    val a = Forward("Alice", 10)
    val b = Forward("Bob", 11)
    val team1 = Team[Player]("Team1", List(a))
    val team2 = Team[Player]("Team2", List(b))
    val fm = new FootballMatch(team1, team2)

    fm.handleEvent(Goal(23, "Alice"))
    fm.handleEvent(Goal(45, "Bob"))
    fm.handleEvent(GameOver(90))

    // reflectively grab the companion object
    val companion = FootballMatch.getClass.getField("MODULE$").get(null)
    // try to find and invoke unapply(FootballMatch): Option[(String,Int,String,Int)]
    val unapplyResult = Try {
      val m = companion.getClass.getMethod("unapply", classOf[FootballMatch])
      m.invoke(companion, fm).asInstanceOf[Option[(String, Int, String, Int)]]
    }

    unapplyResult match {
      case Failure(_: NoSuchMethodException) =>
        fail("FootballMatch.unapply is not implemented")
      case Failure(err) =>
        fail(s"FootballMatch.unapply threw an unexpected exception: $err")
      case Success(None) =>
        fail("FootballMatch.unapply returned None, but match was over")
      case Success(Some((t1, s1, t2, s2))) =>
        (t1, s1, t2, s2) shouldBe (("Team1", 1, "Team2", 1))
    }
  }

  test("did Germany Win? (if Implemented)") {
    val a = Forward("Alice", 10)
    val b = Forward("Bob", 11)
    val team1 = Team[Player]("Deutschland", List(a))
    val team2 = Team[Player]("Scotland", List(b))
    val fm = new FootballMatch(team1, team2)

    fm.handleEvent(Goal(23, "Alice"))
    fm.handleEvent(GameOver(90))

    // reflectively grab the companion object
    val companion = FootballMatch.getClass.getField("MODULE$").get(null)
    // try to find and invoke didGermanyWin(FootballMatch): Boolean
    val didGermanyWinResult = Try {
      val m = companion.getClass.getMethod("didGermanyWin", classOf[FootballMatch])
      println(m.invoke(companion, fm))
      m.invoke(companion, fm).asInstanceOf[Boolean]
    }

    didGermanyWinResult match {
      case Failure(_: NoSuchMethodException) =>
        fail("FootballMatch.didGermanyWin is not implemented")
      case Failure(err) =>
        fail(s"FootballMatch.didGermanyWin threw an unexpected exception: $err")
      case Success(result) =>
        result shouldBe true // or false, depending on the game logic
    }
  }
}