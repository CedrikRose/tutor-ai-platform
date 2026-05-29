import { useNavigate } from 'react-router-dom';
import './About.css';

function About() {
  const navigate = useNavigate();

  return (
    <div className="about-page">
      <div className="about-container">
        <button onClick={() => navigate('/')} className="back-button">
          ← Zurück zum Chatbot
        </button>

        <div className="about-content">
          <section className="about-section">
            <h2>Über Tutor AI</h2>
            <p>
              Tutor AI ist eine innovative Lernplattform für Universitäten und Professoren,
              die Kurse durch intelligente, kontextbezogene Chatbots revolutioniert.
            </p>

            <div className="subsection">
              <h3>Für Studierende:</h3>
              <p>
                Wir stellen den Studierenden einen KI-Tutor zur Verfügung, dem die gesamten
                Kursmaterialien (Vorlesungsfolien, Tutorien, Hausaufgaben) direkt vorliegen.
                Der Chatbot kann spezifische Fragen zum Stoff beantworten, ohne dass die
                Studierenden die Materialien selbst durchsuchen müssen. Er bietet punktgenaue
                Erklärungen im direkten Kontext des jeweiligen Kurses.
              </p>
            </div>

            <div className="subsection">
              <h3>Für Lehrende:</h3>
              <p>
                Tutor AI geht weit über einen einfachen Chatbot hinaus. Die kursspezifischen
                Chatverläufe werden anonymisiert analysiert, um häufige Fehlerquellen,
                Verständnislücken und wertvolles Feedback zu identifizieren. Diese Insights
                werden den Professoren in übersichtlicher Form zur Verfügung gestellt, damit
                sie ihre Lehre schneller und detailreicher auf die tatsächlichen Bedürfnisse
                der Studierenden einstellen können.
              </p>
            </div>
          </section>

          <section className="about-section">
            <h2>Über den Gründer</h2>
            <p>
              Mein Name ist Cedrik Rosemann, ich bin Student der Wirtschaftsinformatik im 4.
              Bachelor-Semester an der TU Berlin. Mit Tutor AI möchte ich die Brücke zwischen
              modernster KI-Technologie und akademischer Lehre schlagen.
            </p>
          </section>

          <section className="about-section impressum">
            <h2>Impressum</h2>
            <p><strong>Angaben gemäß § 5 TMG:</strong></p>
            <p>
              Cedrik Rosemann<br />
              Gunterstraße 10<br />
              14513 Teltow<br />
              Deutschland
            </p>
            <p><strong>Kontakt:</strong></p>
            <p>
              E-Mail: <a href="mailto:cedrik.rosemann@tutor-ai.me">cedrik.rosemann@tutor-ai.me</a><br />
              Telefon: <a href="tel:+491632905333">+49 163 2905333</a>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

export default About;
