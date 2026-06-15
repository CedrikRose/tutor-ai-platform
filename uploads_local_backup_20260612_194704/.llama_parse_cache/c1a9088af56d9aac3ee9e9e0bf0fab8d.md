# PROGRAMMIEREN II

## KAPITEL 5: VON COLLECTIONS ZU MONADEN - FUNKTIONELLES ARBEITEN MIT DATEN

**PROF. DR. AXEL KÜPPER**
**TECHNISCHE UNIVERSITÄT BERLIN &#x26; T-LABS**
**SERVICE-CENTRIC NETWORKING**
**T-LABS**



# OPTION, SOME &#x26; NONE

## WAS IST HIER DAS PROBLEM?

```scala
val findProductNameByIdUnsafe: Int => String = id =>
if (id == 1) "T-Shirt"
else null

val name = findProductNameByIdUnsafe(999)
println(name.toUpperCase)
```

### Erklärung des Problems

In dem obigen Code wird eine Funktion `findProductNameByIdUnsafe` definiert, die einen Produktnamen basierend auf einer ID zurückgibt. Wenn die ID 1 ist, wird "T-Shirt" zurückgegeben, andernfalls wird `null` zurückgegeben.

Das Problem tritt auf, wenn die Funktion mit einer ID aufgerufen wird, die nicht existiert (in diesem Fall 999). Der Rückgabewert ist `null`, und der Versuch, `toUpperCase` auf `null` aufzurufen, führt zu einer `NullPointerException`.

## Lösung mit Option

Um dieses Problem zu vermeiden, können wir `Option` verwenden, um sicherzustellen, dass wir mit einem möglichen `null`-Wert sicher umgehen können.

```scala
val findProductNameById: Int => Option[String] = id =>
if (id == 1) Some("T-Shirt")
else None

val nameOption = findProductNameById(999)
nameOption match {
case Some(name) => println(name.toUpperCase)
case None => println("Produkt nicht gefunden")
}
```

### Erklärung der Lösung

In dieser verbesserten Version gibt die Funktion `findProductNameById` ein `Option[String]` zurück. Wenn das Produkt gefunden wird, wird `Some("T-Shirt")` zurückgegeben, andernfalls `None`.

Durch die Verwendung von Pattern Matching können wir sicherstellen, dass wir nur dann `toUpperCase` aufrufen, wenn tatsächlich ein Produktname vorhanden ist. Andernfalls geben wir eine entsprechende Nachricht aus.



# OPTION, SOME &#x26; NONE

## WAS IST HIER DAS PROBLEM?

```scala
val findProductNameByIdUnsafe: Int => String = id =>
if (id == 1) "T-Shirt"
else null

val name = findProductNameByIdUnsafe(999)
println(name.toUpperCase)
```

In vielen Fällen kann eine Funktion keinen sinnvollen Rückgabewert liefern – zum Beispiel wenn ein Kunde in der Datenbank nicht gefunden wird. Im imperativen Stil braucht man viele `if`, `try` und `catch`, um solche Ausnahmen abzufangen und Null-Pointer-Exception zu vermeiden. In Scala und Java existiert `null`, aber man benutzt es fast nie. Stattdessen verwendet man den generischen Container `Option[T]` in Scala (oder `Optional<t>` in Java) für "Wert vorhanden oder nicht".

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5</t>



# OPTION, SOME &#x26; NONE

## OPTION ALS ALTERNATIVE ZU NULL

```scala
Option[A]
&#x3C;<abstract>>
+ get: T
+ contains(...): Boolean
+ flatMapB Some("T-Shirt")
else None

val name = findProductNameById(999).getOrElse("Unknown")
println(name.toUpperCase)
```

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**</abstract>



# OPTION, SOME &#x26; NONE

## OPTION ALS ALTERNATIVE ZU NULL

### Option[A]
```scala
&#x3C;<abstract>>

+ get: T
+ contains(...): Boolean
+ flatMapB.

----

### PROGRAMMIEREN II | 2026 | KAPITEL 5    5</abstract>



# OPTION, SOME &#x26; NONE

## OPTION ALS ALTERNATIVE ZU NULL

Wenn eine Variable vom Typ `Option[A]` einen Wert vom Typ `Some[+A]` enthält, bedeutet dies, dass ein Wert vom Typ `A` existiert und dieser durch `Some[+A]` gekapselt wird. Wenn die Variable einen Wert vom Typ `None` enthält, bedeutet dies, dass kein Wert existiert.

`Option[A]` definiert zahlreiche Methoden, um an den inneren Wert vom Typ `A` zu gelangen oder um diesen Wert zu verarbeiten und als Ergebnis der Bearbeitung einen neuen Wert vom Typ `Option[A]` zu generieren.

Die Methode `getOrElse` ist eine Methode, die entweder den Wert vom Typ `A` zurückgibt, falls dieser existiert, oder einen Standardwert, der beim Aufruf als Argument übergeben wurde.

```scala
val findProductNameById: Int => Option[String] = id =>
if (id == 1) Some("T-Shirt")
else None

val name = findProductNameById(999).getOrElse("Unknown")
println(name.toUpperCase)
```

## PROGRAMMIEREN II | 2026 | KAPITEL 5



# OPTION, SOME &#x26; NONE

## OPTION API

### PROGRAMMIEREN II | 2026 | KAPITEL 5

For more information, visit the Scala Option API documentation.



# OPTION, SOME &#x26; NONE

## BEISPIELMETHODEN AUF OPTION

```scala
val findProductNameById: Int => Option[String] = id =>
if (id == 1) Some("T-Shirt")
else None
```

### VERWENDUNG MIT GETORELSE
```scala
val name = findProductNameById(999).getOrElse("Unknown")
println(name.toUpperCase)
```

### VERWENDUNG MIT GET (NICHT EMPFOHLEN, GEFÄHRLICH)
```scala
val name = findProductNameById(999).get
```

### VERWENDUNG MIT FOREACH
```scala
findProductNameById(1).foreach(p => println(s"YAOS verkauft: $p"))
```

### VERWENDUNG MIT FILTER
```scala
val filtered = findProductNameById(1).filter(_.startsWith("T"))
println(filtered)
```

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# OPTION, SOME &#x26; NONE
## SCALA OPTION VS JAVA OPTIONAL

### Scala Example
```scala
val findProductNameById: Int => Option[String] = id => {
if (id == 1) Some("T-Shirt")
else None
}

val name = findProductNameById(1).getOrElse("Unknown")
println(name.toUpperCase)
```

### Java Example
```java
import java.util.Optional;

Optional<string> findProductNameById(int id) {
if (id == 1) {
return Optional.of("T-Shirt");
} else {
return Optional.empty();
}
}

var name = findProductNameById(1).orElse("Unknown");
System.out.println(name.toUpperCase());
```

----

### Summary
- **Scala's `Option`**: Represents a value that may or may not be present. It can be `Some(value)` or `None`.
- **Java's `Optional`**: A container object which may or may not contain a non-null value. It can be created using `Optional.of(value)` or `Optional.empty()`.

### Key Differences
- Scala's `Option` is a more functional approach, while Java's `Optional` is more object-oriented.
- Scala provides more built-in methods for handling `Option`, making it easier to work with.

----

### Conclusion
Both `Option` in Scala and `Optional` in Java serve the purpose of avoiding null references, but they do so in different ways that reflect the paradigms of their respective languages.</string>



# OPTION, SOME &#x26; NONE
## SCALA OPTION VS JAVA OPTIONAL

### Java Optional
```java
import java.util.Optional;

Optional<string> findProductNameById(int id) {
if (id == 1) {
return Optional.of("T-Shirt");
} else {
return Optional.empty();
}
}

var name = findProductNameById(1).orElse("Unknown");
System.out.println(name.toUpperCase());
```

### Comparison
- `Optional<t>` in Java is similar to `Option[T]` in Scala.
- Both are used to avoid `null`.
- Scala's `Option[T]` is more compact, expressive, and better integrated into the language core.
- Java's `Optional<t>` requires more boilerplate but has been type-safe since Java 8.

----

### PROGRAMMIEREN II | 2026 | KAPITEL 5</t></t></string>



# OPTION, SOME &#x26; NONE
## JAVA OPTIONAL API

----

### PROGRAMMIEREN II | 2026 | KAPITEL 5

For more information, refer to the Java Optional API documentation.

----

### Overview of Optional

The `Optional` class is a container object which may or may not contain a value. It is a way to express the idea of "optional" values in Java, helping to avoid `NullPointerExceptions`.

### Key Methods

- **of(T value)**: Returns an `Optional` with the specified present non-null value.

```java
Optional<string> optional = Optional.of("Hello");
```

- **ofNullable(T value)**: Returns an `Optional` describing the specified value, if non-null, otherwise an empty `Optional`.

```java
Optional<string> optional = Optional.ofNullable(null);
```

- **empty()**: Returns an empty `Optional` instance.

```java
Optional<string> optional = Optional.empty();
```

- **isPresent()**: Returns `true` if there is a value present, otherwise `false`.

```java
if (optional.isPresent()) {
System.out.println(optional.get());
}
```

- **ifPresent(Consumer action)**: If a value is present, it invokes the specified consumer with the value, otherwise does nothing.

```java
optional.ifPresent(value -> System.out.println(value));
```

- **orElse(T other)**: Returns the value if present, otherwise returns `other`.

```java
String value = optional.orElse("Default Value");
```

- **orElseGet(Supplier other)**: Returns the value if present, otherwise invokes the supplier and returns the result.

```java
String value = optional.orElseGet(() -> "Default Value from Supplier");
```

- **orElseThrow(Supplier exceptionSupplier)**: Returns the contained value, if present, otherwise throws an exception produced by the provided supplier.

```java
String value = optional.orElseThrow(() -> new IllegalArgumentException("Value not present"));
```

### Example Usage

```java
public class OptionalExample {
public static void main(String[] args) {
Optional<string> optional = Optional.ofNullable(getValue());

optional.ifPresent(value -> System.out.println("Value is: " + value));
String result = optional.orElse("No Value");
System.out.println(result);
}

private static String getValue() {
return null; // Simulating a missing value
}
}
```

### Summary

Using `Optional` can help you write cleaner and more robust code by explicitly handling the presence or absence of values, reducing the risk of `NullPointerExceptions`.</string></string></string></string>



# JAVA STREAMS
## EINFÜHRENDES BEISPIEL

```java
public class Product {
private final String name;
private final boolean available;
private final int price; // Preis in Eurocent
private final Category category;

public enum Category {
ELECTRONICS, FASHION, BOOKS, FOOD, OTHER
}

public Product(String name, boolean available, int price, Category category) {
this.name = name;
this.available = available;
this.price = price;
this.category = category;
}

public String getName() {
return name;
}

public boolean isAvailable() {
return available;
}

public int getPrice() {
return price;
}

public Category getCategory() {
return category;
}

@Override
public String toString() {
return name + " (" + (price / 100.0) + " €)";
}
}
```

----

### PROGRAMMIEREN II | 2026 | KAPITEL 5



# JAVA STREAMS
## EINFÜHRENDES BEISPIEL

```java
List catalog = Arrays.asList(
new Product("Laptop", true, 89900, Product.Category.ELECTRONICS),
new Product("T-Shirt", true, 2499, Product.Category.FASHION),
new Product("Kochbuch", true, 1899, Product.Category.BOOKS),
new Product("Smartphone", false, 69900, Product.Category.ELECTRONICS),
new Product("Bio-Honig", true, 799, Product.Category.FOOD),
new Product("Bluetooth-Lautsprecher", true, 4599, Product.Category.ELECTRONICS),
new Product("Sneakers", false, 5999, Product.Category.FASHION),
new Product("USB-C Kabel", true, 999, Product.Category.ELECTRONICS),
new Product("Leder-Geldbörse", true, 3999, Product.Category.FASHION),
new Product("Romanbestseller", true, 1499, Product.Category.BOOKS),
new Product("Kaffeemaschine", true, 6999, Product.Category.ELECTRONICS),
new Product("Fitness-Tracker", true, 3499, Product.Category.ELECTRONICS),
new Product("Müsli-Riegel 12er Pack", true, 299, Product.Category.FOOD),
new Product("Gaming-Maus", true, 4999, Product.Category.ELECTRONICS),
new Product("Designer-Schal", false, 6999, Product.Category.FASHION),
new Product("USB-Stick 128GB", true, 1299, Product.Category.ELECTRONICS),
new Product("Tee-Geschenkset", true, 1799, Product.Category.FOOD),
new Product("Smartwatch", true, 7999, Product.Category.ELECTRONICS),
new Product("Winterjacke", false, 12999, Product.Category.FASHION),
new Product("Thriller-Hörbuch", true, 999, Product.Category.BOOKS),
new Product("Espressokocher", true, 3499, Product.Category.FOOD),
new Product("Notebook-Rucksack", true, 4599, Product.Category.FASHION),
new Product("Geschenkbox 'Italien'", true, 2499, Product.Category.FOOD),
new Product("Bildband Architektur", true, 2999, Product.Category.BOOKS),
new Product("Wireless Charger", true, 2399, Product.Category.ELECTRONICS)
);
```

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**</product>



# JAVA STREAMS
## IMPERATIVER PROGRAMMIERSTIL

```java
// Schritt 1: Produkte unter 50 € und verfügbar herausfiltern
List affordableProducts = new ArrayList&#x3C;>();
for (Product p : catalog) {
if (p.isAvailable() &#x26;&#x26; p.getPrice() &#x3C; 50) {
affordableProducts.add(p);
}
}

// Schritt 2: Produkte nach Preis aufsteigend sortieren
Collections.sort(affordableProducts, new Comparator() {
public int compare(Product p1, Product p2) {
return Integer.compare(p1.getPrice(), p2.getPrice());
}
});

// Schritt 3: Nur die Namen extrahieren
List<string> productNames = new ArrayList&#x3C;>();
for (Product p : affordableProducts) {
productNames.add(p.getName());
}

// Ausgabe
System.out.println("Verfügbare Produkte unter 50 €, sortiert nach Preis:");
for (String name : productNames) {
System.out.println(name);
}
```

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5</string></product></product>



# JAVA STREAMS

## IMPERATIVER PROGRAMMIERSTIL

```java
// Schritt 1: Produkte unter 50 € und verfügbar herausfiltern
List affordableProducts = new ArrayList&#x3C;>();
for (Product p : catalog) {
if (p.isAvailable() &#x26;&#x26; p.getPrice() &#x3C; 50) {
affordableProducts.add(p);
}
}

// Schritt 2: Produkte nach Preis aufsteigend sortieren
Collections.sort(affordableProducts, new Comparator() {
public int compare(Product p1, Product p2) {
return Integer.compare(p1.getPrice(), p2.getPrice());
}
});

// Schritt 3: Nur die Namen extrahieren
List<string> productNames = new ArrayList&#x3C;>();
for (Product p : affordableProducts) {
productNames.add(p.getName());
}

// Ausgabe
System.out.println("Verfügbare Produkte unter 50 €, sortiert nach Preis:");
for (String name : productNames) {
System.out.println(name);
}
```

### Anmerkungen
- Altes Java (&#x3C;8) erzwingt die Bearbeitung von Collections mit externer Iteration.
- Programmierer programmiert das Wie: "Durchlaufe alle Elemente einer Collection iterativ und berechne dann dieses und mach' danach jenes!"

### COLLECTIONS ARE ABOUT DATA
- Sammlungen wie List, Set und Map speichern Daten.
- Sie sind zustandsbehaftet und enthalten Elemente, auf die man direkt zugreifen kann.
- Man kann Elemente hinzufügen, entfernen, sortieren, etc.
- Eine Collection ist ein Container für Daten.

----

PROGRAMMIEREN II | 2026 | KAPITEL 5</string></product></product>



# JAVA STREAMS
## DEKLARATIVER PROGRAMMIERSTIL

```java
.filter(p -> p.isAvailable() &#x26;&#x26; p.getPrice() &#x3C; 5000)
.sorted(Comparator.comparing(Product::getPrice))
.map(Product::getName) // BEISPIEL VON LETZTER FOLIE
.collect(Collectors.toList()); // Schritt 1: Produkte unter 50 € und verfügbar herausfiltern

List affordableProducts = new ArrayList&#x3C;>();
System.out.println("Verfügbare Produkte unter 50 € (Streams):");
for (Product p : catalog) {
if (p.isAvailable() &#x26;&#x26; p.getPrice() &#x3C; 5000) {
affordableProducts.add(p);
}
}

// Schritt 2: Produkte nach Preis aufsteigend sortieren
Collections.sort(affordableProducts, new Comparator() {
public int compare(Product pl, Product p2) {
return Integer.compare(pl.getPrice(), p2.getPrice());
}
});

// Schritt 3: Nur die Namen extrahieren
List<string> productNames = new ArrayList&#x3C;>();
for (Product p : affordableProducts) {
productNames.add(p.getName());
}

// Ausgabe
System.out.println("Verfügbare Produkte unter 50 €, sortiert nach Preis:");
for (String name : productNames) {
System.out.println(name);
}
```

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5</string></product></product>



# JAVA STREAMS

## DIE STREAM API

----

### PROGRAMMIEREN II | 2026 | KAPITEL 5

Java Stream API Documentation

----

### Einführung in Streams

Streams sind eine neue Art, mit Daten in Java zu arbeiten. Sie ermöglichen eine funktionale Programmierung und bieten eine einfache Möglichkeit, Daten zu verarbeiten.

### Grundlegende Operationen

Streams unterstützen verschiedene Arten von Operationen:

1. **Intermediate Operations**: Diese Operationen sind lazy und geben einen neuen Stream zurück. Beispiele sind `filter()`, `map()`, und `sorted()`.
2. **Terminal Operations**: Diese Operationen sind nicht lazy und produzieren ein Ergebnis oder eine Nebenwirkung. Beispiele sind `collect()`, `forEach()`, und `reduce()`.

### Beispiel: Verwendung von Streams

Hier ist ein einfaches Beispiel, das zeigt, wie man Streams in Java verwendet:

```java
import java.util.Arrays;
import java.util.List;

public class StreamExample {
public static void main(String[] args) {
List<string> names = Arrays.asList("Anna", "Bob", "Charlie", "Diana");

names.stream()
.filter(name -> name.startsWith("A"))
.forEach(System.out::println);
}
}
```

### Wichtige Methoden

| Methode         | Beschreibung                                           |
|-----------------|-------------------------------------------------------|
| `filter(Predicate)` | Filtert Elemente basierend auf einem Kriterium.     |
| `map(Function)`     | Wandelt Elemente in eine andere Form um.            |
| `collect(Collector)`| Aggregiert die Elemente in eine Sammlung.            |
| `reduce(BinaryOperator)` | Reduziert die Elemente auf einen einzelnen Wert. |

### Mathematische Operationen

Streams können auch für mathematische Operationen verwendet werden. Zum Beispiel:

- **Summe**: `int sum = numbers.stream().mapToInt(Integer::intValue).sum();`
- **Durchschnitt**: `double average = numbers.stream().mapToInt(Integer::intValue).average().orElse(0);`

### Diagramm: Stream-Pipeline

```
[Source] -> [Intermediate Operations] -> [Terminal Operation]
```

**Abbildung 1**: Stream-Pipeline

### Fazit

Die Stream API in Java bietet eine leistungsstarke und flexible Möglichkeit, mit Daten zu arbeiten. Sie ermöglicht eine klare und prägnante Syntax, die die Lesbarkeit und Wartbarkeit des Codes verbessert.</string>



# JAVA STREAMS

## STRUKTUR VON STREAMS

```
Lambda    Lambda    Lambda    Lambda
catalog  filter  sorted  map  collect  >productNames
```

### Intermediate operations and Terminal operation

```java
List<string> productNames = catalog.stream()
.filter(p -> p.isAvailable() &#x26;&#x26; p.getPrice() &#x3C; 5000)
.sorted(Comparator.comparing(Product::getPrice))
.map(Product::getName)
.collect(Collectors.toList());

System.out.println("Verfügbare Produkte unter 50 € (Streams):");
productNames.forEach(System.out::println);
```

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5</string>



# JAVA STREAMS

## STRUKTUR VON STREAMS

```
Lambda    Lambda    Lambda    Lambda
catalog             filter    sorted        map        collect         >productNames
```

### Intermediate operations    Terminal operation

----

### STREAMS SIND ÜBER BERECHNUNGEN

**Streams** sind eine Sequenz von Elementen, die von einer Quelle erzeugt und auf denen Operationen zur Datenverarbeitung angewendet werden.

- Ein Stream beschreibt eine Berechnung über Daten – keine Sammlung an sich.
- Streams speichern keine Daten, sondern Transformationen (z.B. filtern, abbilden, aggregieren).
- Sie sind lazy, d.h. es passiert nichts, bis eine Terminaloperation aufgerufen wird.
- Bei geordneten Quellen wird die Ordnung im Stream erhalten.
- Die Bearbeitung von Daten in einem Stream kann sequenziell oder parallel erfolgen.
- Ein Stream ist ein Ablaufplan, d.h. eine Pipeline von Operationen über Daten.

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**    19



# JAVA STREAMS

## STRUKTUR VON STREAMS

```
Lambda    Lambda    Lambda    Lambda
catalog                    filter        sorted               map  collect     >productNames
```

### BESTANDTEILE VON STREAM-PIPELINES

- **Datenquelle** (z.B. eine Collection) als Anfang der Pipeline
- **Intermediate Operations** als Zwischenbearbeitungsschritte
- Verwenden einen Stream als Eingabe und produzieren einen Stream als Ausgabe
- Intermediate Operations sind lazy, d.h. sie werden erst dann ausgeführt, wenn die Terminal Operation der Pipeline aufgerufen wird
- **Terminal Operation** als Abschluss der Pipeline

### INTERMEDIATE OPERATIONS

- **Intermediate Operations** verwenden einen Stream als Eingabe und produzieren einen Stream als Ausgabe.
- Intermediate Operations sind lazy, d.h. sie werden erst dann ausgeführt, wenn die Terminal Operation der Pipeline aufgerufen wird.

### TERMINAL OPERATIONS

- **Terminal Operations** produzieren das Ergebnis einer Pipeline, welches jeden Datentyp (z.B. List, Integer, void) mit Ausnahme von Stream haben kann.
- Jede Stream-Pipeline muss mit einer Terminal Operation abgeschlossen werden.

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# JAVA STREAMS
## KLASSIFIKATION VON STREAM-OPERATIONEN

### Stream-Operationen

| Intermediate Operations | Terminal Operations |
|-------------------------|---------------------|
| Geben Streams zurück    | Konsumieren Streams  |
| Sind lazy               | Sind eager           |
| Short-circuiting        | Short-circuiting     |
| Sequentiell/parallel    | Haben Seiteneffekte  |

#### Intermediate Operations
- Stateless
- `map`
- `filter`
- `distinct`
- Stateful
- `sorted`
- `limit`
- `peek`

#### Terminal Operations
- `sum`
- `collect`
- `min`
- `reduce`
- `max`
- `count`
- `average`

----

PROGRAMMIEREN II | 2026 | KAPITEL 5    21



# JAVA STREAMS

## KLASSIFIKATION VON STREAM-OPERATIONEN

### Stream-Operationen

#### STATELESS
Zustandslose Operationen (Stateless Operations) basieren ausschließlich auf ihrer Funktionalität, dem übergebenen Lambda-Ausdruck bzw. der Methodenreferenz und dem jeweiligen Eingabeelement.

| Intermediate Operations | Terminal Operations |
|------------------------|---------------------|
| Geben Streams zurück    | Konsumieren Streams  |
| Sind lazy               | Sind eager           |
| .                       | .                    |
| Short-circuiting       | Short-circuiting     |
| Sequentiell/parallel    | Haben Seiteneffekte  |

#### STATEFUL
Zustandsbehaftete Operationen (Stateful Operations) basieren auf ihrer Funktionalität, dem übergebenen Lambda-Ausdruck bzw. der Methodenreferenz, dem jeweiligen Eingabeelement und Kontextinformationen. Bei Kontextinformationen handelt es sich um Werte, die basierend auf den bisherigen Elementen des Streams berechnet wurden.

| Stateless | Stateful |
|-----------|----------|
| map       | .sum     |
| filter    | .min     |
| distinct  | .reduce  |
| unsorted  | max      |
| limit     | .count   |
| peek      | .average  |

----

PROGRAMMIEREN II | 2026 | KAPITEL 5



# JAVA STREAMS
## FILTERN VON ELEMENTEN

```java
List availableProducts = catalog.stream()
.filter(Product::isAvailable)
.collect(Collectors.toList());
```

`filter` liefert einen Ausgabe-Stream, der alle Elemente des Streams enthält, die das an `filter` übergebene Prädikat erfüllen.

| Stream       | Stream                      | List          |
|--------------|-----------------------------|---------------|
|     |                    |      |

PROGRAMMIEREN II | 2026 | KAPITEL 5                                                                          23</product></product></product></product>



# JAVA STREAMS
## FILTERN VON ELEMENTEN

```java
catalog.stream()
.filter(p -> p.getPrice() &#x3C; 5000)
.map(Product::getCategory)
.distinct()
.forEach(System.out::println);
```

### Erklärung der Schritte:
1. **filter**: Filtert die Produkte, deren Preis unter 5000 liegt.
2. **map**: Wandelt die gefilterten Produkte in ihre Kategorien um.
3. **distinct**: Liefert einen Ausgabe-Stream, der nur die unterschiedlichen Elemente aus dem Eingabe-Stream enthält.
4. **forEach**: Gibt jede Kategorie in der Konsole aus.

### Beispielhafte Produktpreise und Kategorien:
| Preis  | Preis  | Kategorie | Kategorie | Ausgabe       |
|--------|--------|-----------|-----------|---------------|
| 2499   | 2499   | FASHION   | FASHION   | "FASHION"     |
| 1899   | 1899   | BOOKS     | BOOKS     | "BOOKS"       |
| 5999   |        |           |           |               |
| 12559  |        |           |           |               |
| 9999   |        |           |           |               |
| 2349   | 2349   | FASHION   |           |               |

### Typen der Streams:
- `Stream`: Der Eingabe-Stream von Produkten.
- `Stream<category>`: Der Ausgabe-Stream von Kategorien.

----

PROGRAMMIEREN II | 2026 | KAPITEL 5</category></product>



# JAVA STREAMS

## FILTERN VON ELEMENTEN

```java
List limitedList = catalog.stream()
.filter(p -> p.getPrice() > 2000)
.limit(3)
.collect(Collectors.toList());
```

### Erklärung
- `filter`: Filtert die Elemente des Streams basierend auf dem angegebenen Prädikat (in diesem Fall `p -> p.getPrice() > 2000`).
- `limit`: Liefert einen Ausgabe-Stream mit der durch den Parameter `maxSize` spezifizierten Anzahl von Elementen des Streams.
- `collect`: Sammelt die Elemente des Streams in eine Liste.

### Beispielpreise
| Preis  |
|--------|
| 2499   |
| 1899   |
| 5999   |
| 12559  |
| 9999   |
| 2349   |

### Stream Typen
- `Stream`: Der ursprüngliche Stream von Produkten.
- `Stream`: Der gefilterte Stream von Produkten.
- `Stream`: Der limitierte Stream von Produkten.
- `List`: Die finale Liste der Produkte nach dem Filtern und Limiting.

----

PROGRAMMIEREN II | 2026 | KAPITEL 5                                                                            25</product></product></product></product></product>



# JAVA STREAMS
## FILTERN VON ELEMENTEN

```java
List skippedProducts = catalog.stream()
.filter(p -> p.getPrice() > 2000)
.skip(2)
.collect(Collectors.toList());
```

### Erklärung
`skip` liefert einen Ausgabe-Stream ohne die durch den Parameter n spezifizierten ersten n Elemente des Eingabe-Streams.

| Preis  |
|--------|
| 2499   |
| 1899   |
| 5999   |
| 12559  |
| 9999   |
| 2349   |

### Stream-Diagramm
```
Stream -> Stream -> Stream -> List
```

PROGRAMMIEREN II | 2026 | KAPITEL 5</product></product></product></product></product>



# JAVA STREAMS

## Abbildungen

```java
List<string> labeledProducts = catalog.stream()
.map(p -> p.getName() + " - " + (p.getPrice() / 100.0) + " €")
.collect(Collectors.toList());

labeledProducts.forEach(System.out::println);
```

### Produktkatalog

| Produkt       | Preis  |
|---------------|--------|
| T-Shirt       | 24.99  |
| Kochbuch      | 18.99  |
| Bio-Honig     | 7.99   |
| USB-C Kabel   | 9.99   |
| Laptop        | 899.00 |
| Sneakers      | 59.99  |

### Erläuterung

- `map` wendet eine Funktion auf jedes Element des Streams an und erzeugt einen neuen Stream mit den Rückgabewerten der Funktion.

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5

### Seite 27</string>



# JAVA STREAMS

## FINDEN UND ABGLEICHEN

### anyMatch – GIBT ES PRODUKTE UNTER €100?
```java
if (catalog.stream().anyMatch(p -> p.getPrice() &#x3C; 100)) {
System.out.println("Ja, es gibt Produkte unter 100 €!");
}
```
`anyMatch` prüft, ob mindestens ein Element das Prädikat erfüllt.

### allMatch – HABEN ALLE VERFÜGBAREN PRODUKTE EINEN PREIS UNTER 1000€?
```java
boolean isCheap = catalog.stream()
.filter(Product::isAvailable)
.allMatch(p -> p.getPrice() &#x3C; 1000);
```
`allMatch` prüft, ob alle Elemente das Prädikat erfüllen.

### noneMatch – KEIN PRODUKT ÜBER 900€?
```java
boolean isLuxuryFree = catalog.stream()
.noneMatch(p -> p.getPrice() > 900);
```
`noneMatch` prüft, ob kein Element das Prädikat erfüllt.

----

PROGRAMMIEREN II | 2026 | KAPITEL 5    28



# JAVA STREAMS: FINDEN UND ABGLEICHEN

## findAny – FINDE IRGENDEIN VERFÜGBARES PRODUKT DER KATEGORIE FOOD
```java
Optional maybeFood = catalog.stream()
.filter(p -> p.isAvailable() &#x26;&#x26; p.getCategory() == Product.Category.FooD)
.findAny();
```
```java
maybeFood.ifPresent(p -> System.out.println("Food-Produkt: " + p.getName()));
```
- `findAny` liefert ein beliebiges passendes Element (nicht-deterministisch).

## findFirst – FINDE DAS ERSTE NICHT-VERFÜGBARE PRODUKT ÜBER 50€?
```java
Optional firstUnavailable = catalog.stream()
.filter(p -> !p.isAvailable() &#x26;&#x26; p.getPrice() > 5000)
.findFirst();
```
```java
firstUnavailable.ifPresent(p -> System.out.println("Nicht verfügbar: " + p.getName()));
```
- `findFirst` liefert das erste passende Element (bei geordnetem Stream stabil).

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5    29</product></product>



# JAVA STREAMS
## REDUZIEREN VON STREAMS

```java
Optional<integer> maxPrice = catalog.stream()
.map(Product::getPrice)
.reduce(Integer::max);
```

Die `reduce`-Methode kombiniert alle Elemente eines Streams zu einem einzelnen Wert.

| Produkt      | Preis | max   | Ergebnis |
|--------------|-------|-------|----------|
| T-Shirt      | 2499  | max   | 2499     |
| Kochbuch     | 1899  | max   | 2499     |
| Bio-Honig    | 799   | max   | 2499     |
| USB-C Kabel  | 999   | max   | 2499     |
| Laptop       | 89900 | max   | 89900    |
| Sneakers     | 5999  | max   | 89900    |

| Stream       | Stream       | Optional   |
|--------------|--------------|------------|
| ``  | `<integer>`  | `<integer>`|

----

PROGRAMMIEREN II | 2026 | KAPITEL 5                  30</integer></integer></product></integer>



# JAVA STREAMS

## REDUZIEREN VON STREAMS

```java
int totalPrice = catalog.stream()
.map(Product::getPrice)
.reduce(0, Integer::sum);
```

Die `reduce`-Methode kombiniert alle Elemente eines Streams zu einem einzelnen Wert.

| Produkt         | Preis (Cent) | Zwischensumme (Cent) |
|-----------------|--------------|-----------------------|
| T-Shirt         | 2499         | 2499                  |
| Kochbuch        | 1899         | 4398                  |
| Bio-Honig       | 799          | 5197                  |
| USB-C Kabel     | 999          | 6196                  |
| Laptop          | 89900        | 96096                 |
| Sneakers        | 5999         | 102095                |

| Stream          | Typ                |
|-----------------|--------------------|
| Stream | Stream     |
| Stream<integer> | Stream<integer>     |

PROGRAMMIEREN II | 2026 | KAPITEL 5 31</integer></integer></product></product>



# JAVA STREAMS

## INTERNE BEARBEITUNG VON STREAMS: EAGERNESS VS LAZINESS

```java
String firstCheapProduct = catalog.stream()
.filter(p -> p.isAvailable())
.filter(p -> p.getPrice() &#x3C; 1000)
.map(p -> p.getName() + " - " + (p.getPrice() / 100.0) + " €")
.findFirst()
.get();
```

```java
System.out.println(firstCheapProduct);
```

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5    32



# A STREAMS
## INTERNE BEARBEITUNG VON STREAMS: EAGERNESS VS LAZINESS

### EAGERNESS
| Item                     | Filter                    | Filter                    | Map                     | Find First               |
|--------------------------|--------------------------|--------------------------|-------------------------|--------------------------|
| Laptop                   | Laptop                   | →                        |                         |                          |
| T-Shirt                  | T-Shirt                  | >                        |                         |                          |
| Kochbuch                 |                          | Kochbuch                 | →                       |                          |
| Smartphone               |                          |                          |                         |                          |
| Bio-Honig               | Bio-Honig               |                          | Bio-Honig              | "Bio-Honig - 7.99 €"    |
| Bluetooth-Lautsprecher   | Bluetooth-Lautsprecher   | >                        |                         |                          |
| Sneakers                 |                          |                          |                         |                          |
| USB-C Kabel              | USB-C Kabel              | >                        |                         |                          |
| Leder-Geldbörse          | Leder-Geldbörse          | >                        |                         |                          |
| Romanbesteller           | Romanbesteller           |                          |                         |                          |
| Kaffee-Maschine          | Kaffee-Maschine          |                          |                         |                          |
| Fitness-Tracker          | Fitness-Tracker          |                          | Tracker                 |                          |
| Müsli-Riegel             |                          | Müsli-Riegel            |                         | "Müsli-Riegel - 2.99 €"  |
| Gaming-Maus              | Gaming-Maus              |                          |                         |                          |
| Designer-Schal           |                          |                          |                         |                          |
| USB-Stick                | USB-Stick                |                          |                         |                          |
| Tee-Geschenkset          | Tee-Geschenkset          | >                        |                         |                          |
| Smartwatch               | Smartwatch               |                          | →                       | Winterjacke              |
| Thriller-Hörbuch         | Thriller-Hörbuch         | Thriller-Hörbuch         |                         | "Thriller-Hörbuch - 9.99 €" |
| Espresso-Kocher          | Espresso-Kocher          |                          |                         |                          |
| Notebook-Rucksack        | Notebook-Rucksack        |                          |                         |                          |
| Geschenkbox              | Geschenkbox              |                          |                         |                          |
| Italien                  | Italien                  |                          | Bildband                |                          |
| Architektur              | Architektur              |                          |                         |                          |
| Wireless Charger         | Wireless Charger         | 25                       | Charger                 | 21                       |
|                          | +                        | +                        | 3                       | +                        |
|                          |                          |                          | 50                      |                          |

### Operationen
Operation = Operationen

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**
**Page 33**



# JAVA STREAMS

## INTERNE BEARBEITUNG VON STREAMS: EAGERNESS VS LAZINESS

### EAGERNESS

| Operation        | Result          |
|------------------|-----------------|
| filter           |                 |
| filter           |                 |
| map              |                 |
| findFirst        |                 |

- **Laptop** →
- **T-Shirt** →
- **Kochbuch** >
- **Smartphone**
- **Bio-Honig** → "Bio-Honig - 7.99 €"
- **Bluetooth-Lautsprecher**
- **Sneakers**
- **USB-C Kabel** >
- **Leder-Geldbörse**
- **Romanbesteller**
- **Kaffeemaschine**
- **Fitness-Tracker**
- **Müsli-Riegel** → "Müsli-Riegel - 2.99 €"
- **Gaming-Maus**
- **Designer-Schal**
- **USB-Stick**
- **Tee-Geschenkset**
- **Smartwatch** >
- **Winterjacke**
- **Thriller-Hörbuch** → "Thriller-Hörbuch - 9.99 €"
- **Espresso-Kocher**
- **Notebook-Rucksack**
- **Geschenkbox**
- **Italien Bildband**
- **Architektur**
- **Wireless Charger**

### Zusammenfassung der Eagerness-Strategie

Bei der **Eagerness-Strategie** wird jede Operation auf alle Elemente des jeweiligen Verarbeitungsschrittes angewendet, d.h. alle Elemente werden `filter` zugeführt, alle verbleibenden Elemente werden der zweiten `filter`-Methode zugeführt usw. Es werden alle 25 Produkte einmal oder mehrfach bearbeitet. Insgesamt ergeben sich 50 Operationen, um den Stream zu bearbeiten.

- Alle Zwischenergebnisse müssen gespeichert werden.
- Die Eagerness-Strategie ist schlecht parallelisierbar, da nach jeder Operation die Elemente zusammengeführt und neu verteilt werden müssen.
- Java-Streams verwenden die Eagerness-Strategie nicht.

| Operationen | + Operationen | + Operationen | Operation | = Operationen |
|-------------|---------------|---------------|-----------|---------------|
| 25          | 21            | 3             | 1         | 50            |

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# A STREAMS
## INTERNE BEARBEITUNG VON STREAMS: EAGERNESS VS LAZINESS

### Laziness vs Eagerness in Stream Processing

| Laziness | Eagerness |
|----------|-----------|
| filter   | filter    |
| map      | map       |
| findFirst| findFirst |

#### Example Items
- Laptop
- T-Shirt
- Kochbuch
- Smartphone
- Bio-Honig
- Bluetooth-Lautsprecher
- Sneakers
- USB-C Kabel
- Leder-Geldbörse
- Romanbesteller
- Kaffeemaschine
- Fitness-Tracker
- Müsli-Riegel
- Gaming-Maus
- Designer-Schal
- USB-Stick
- Tee-Geschenkset
- Smartwatch
- Winterjacke
- Thriller-Hörbuch
- Espresso-kocher
- Notebook-Rucksack
- Geschenkbox
- Italien Bildband
- Architektur Wireless Charger

### Operation Count
- Operations: 5 + 4 + 1 + 1 = 11

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# JAVA STREAMS

## INTERNE BEARBEITUNG VON STREAMS: EAGERNESS VS LAZINESS

|          | filter | filter | map | findFirst |
|----------|--------|--------|-----|-----------|
| LAZINESS | Laptop | Laptop | >   |           |
|          | T-Shirt| T-Shirt| >   |           |
|          | Kochbuch| Kochbuch| > |           |
|          | Smartphone | >   |   |           |
|          | Bio-Honig | Bio-Honig | Bio-Honig | "Bio-Honig - 7.99 €" |
|          | Bluetooth-Lautsprecher | | |           |
|          | Sneakers | | |           |
|          | USB-C Kabel | | |           |
|          | Leder-Geldbörse | | |           |
|          | Romanbestseller | | |           |
|          | Kaffeemaschine | | |           |
|          | Fitness-Tracker | | |           |
|          | Müsli-Riegel | | |           |
|          | Gaming-Maus | | |           |
|          | Designer-Schal | | |           |
|          | USB-Stick | | |           |
|          | Tee-Geschenkset | | |           |
|          | Smartwatch | | |           |
|          | Winterjacke | | |           |
|          | Thriller-Hörbuch | | |           |
|          | Espresso-kocher | | |           |
|          | Notebook-Rucksack | | |           |
|          | Geschenkbox | | |           |
|          | Italien | | |           |
|          | Bildband | | |           |
|          | Architektur | | |           |
|          | Wireless Charger | 5 + 4 + 1 + 1 = 11 | | |

### Bei der **Laziness-Strategie** schickt der Stream ein Element komplett durch die Pipeline, bevor das nächste Element bearbeitet wird.

- Sobald die Bearbeitung des Streams komplett ist, wird die Bearbeitung abgebrochen und alle noch nicht behandelten Elemente werden ignoriert.
- Keine Speicherung von Zwischenergebnissen notwendig.
- Die Anzahl der Operationen kann häufig im Vergleich zur Eagerness-Strategie signifikant reduziert werden.
- Die Elemente des Streams können zur Parallelisierung auf verschiedene Threads aufgeteilt werden, ohne dass eine erneute Zusammenführung nach jedem Schritt erforderlich ist.
- Java-Streams verarbeiten Elemente nach der Laziness-Strategie.

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# JAVA STREAMS

## LAZINESS-VERHALTEN VERSCHIEDENER STREAMS

### Beispiel 1

```java
catalog.stream()
.peek(s -> System.out.println("vor 1. filter: " + s))
.filter(p -> p.isAvailable())
.peek(s -> System.out.println("vor 2. filter: " + s))
.filter(p -> p.getPrice() &#x3C; 1000)
.peek(s -> System.out.println("vor map: " + s))
.map(p -> p.getName() + " _ " + (p.getPrice() / 100.0) + " €")
.peek(s -> System.out.println("vor findFirst: " + s))
.findFirst();
```

### Beispiel 2

```java
catalog.stream()
.peek(s -> System.out.println("vor filter: " + s))
.filter(p -> p.isAvailable() &#x26;&#x26; p.getPrice() &#x3C; 5000)
.peek(s -> System.out.println("vor sorted: " + s))
.sorted(Comparator.comparing(Product::getPrice))
.peek(s -> System.out.println("vor map: " + s))
.map(Product::getCategory)
.peek(s -> System.out.println("vor distinct: " + s))
.distinct()
.peek(s -> System.out.println("vor forEach: " + s))
.forEach(System.out::println);
```

----

### PROGRAMMIEREN II | 2026 | KAPITEL 5

----

### Anmerkungen

- Die Verwendung von `peek` ermöglicht es, den Zustand der Stream-Elemente während der Verarbeitung zu beobachten.
- Die Filter- und Sortieroperationen sind lazy, was bedeutet, dass sie erst ausgeführt werden, wenn eine terminale Operation wie `collect` oder `forEach` aufgerufen wird.
- Die Verwendung von `distinct` entfernt doppelte Elemente aus dem Stream basierend auf der `equals`-Methode der Objekte.



# JAVA STREAMS

## SHORT-CIRCUITING

| Operation   | Intermediate oder Terminal | Beschreibung                                                                 |
|-------------|----------------------------|-----------------------------------------------------------------------------|
| anyMatch    | T                          | Liefert true, sobald ein passendes Element gefunden wurde                  |
| allMatch    | T                          | Liefert false, sobald ein nicht-passendes Element gefunden wurde           |
| noneMatch   | T                          | Liefert false, sobald ein passendes Element gefunden wurde                 |
| findFirst   | T                          | Gibt das erste Element zurück und beendet die Verarbeitung                  |
| findAny     | T                          | Gibt ein beliebig passendes Element zurück                                  |
| limit       | I                          | Begrenzung auf n Elemente                                                  |

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5    38



# JAVA STREAMS
## SHORT-CIRCUITING

| Operation      | Intermediate oder Terminal | Beschreibung                                                                 |
|----------------|----------------------------|-----------------------------------------------------------------------------|
| anyMatch       | T                          | Liefert true, sobald ein passendes Element gefunden wurde                  |
| allMatch       | T                          | Liefert false, sobald ein nicht-passendes Element gefunden wurde           |
| noneMatch      | T                          | Liefert false, sobald ein passendes Element gefunden wurde                  |
| findFirst      | T                          | Gibt das erste Element zurück und beendet die Verarbeitung                  |
| findAny        | T                          | Gibt ein beliebig passendes Element zurück                                  |
| limit          | I                          | Begrenzung auf n Elemente                                                  |

Eine **Short-Circuit-Operation** ist eine Terminal- oder Intermediate-Operation in einem Java-Stream, die nicht den gesamten Stream verarbeiten muss, sondern bei Erreichen eines bestimmten Ergebnisses die Ausführung frühzeitig beendet. Short-Circuit-Operationen sind effizienter als die vollständige Verarbeitung und kombiniert mit Lazy Evaluation besonders leistungsfähig.

Nicht short-circuit-fähig sind `map`, `filter`, `sorted`, `distinct`, `collect`, `forEach` und `reduce`, diese Operationen verarbeiten immer alle relevanten Elemente des Streams.

----

PROGRAMMIEREN II | 2026 | KAPITEL 5



# SCALA COLLECTIONS OVERVIEW

## Scala Collections

### Immutable Collections
- **Iterable**: `&#x3C;<trait>>`
- **Set**: `&#x3C;<trait>>`
- **HashSet**
- **ListSet**
- **SortedSet**
- **Map**: `&#x3C;<trait>>`
- **HashMap**
- **SortedMap**
- **ListMap**
- **VectorMap**
- **Seq**: `&#x3C;<trait>>`
- **List**
- **Vector**
- **LazyList**
- **Queue**
- **Range**

### Mutable Collections
- **Iterable**: `&#x3C;<trait>>`
- **Set**: `&#x3C;<trait>>`
- **HashSet**
- **LinkedHashSet**
- **SortedSet**
- **MultiMap**
- **Map**: `&#x3C;<trait>>`
- **HashMap**
- **WeakHashMap**
- **ListMap**
- **TreeMap**
- **Seq**: `&#x3C;<trait>>`
- **ArrayBuffer**
- **ListBuffer**
- **ArrayDeque**
- **Stack**
- **Queue**

### Traits Overview
| Trait          | Description          |
|----------------|----------------------|
| `Iterable`     | Base trait for all collections |
| `Set`          | Collection of unique elements |
| `Map`          | Collection of key-value pairs |
| `Seq`          | Ordered collections |

### Additional Types
- **IndexedSeq**: `&#x3C;<trait>>`
- **Buffer**: `&#x3C;<trait>>`
- **BitSet**: `&#x3C;<trait>>`
- **StringBuilder**: `&#x3C;<trait>>`

----

### Summary
Scala provides a rich set of collections that can be categorized into immutable and mutable types, each serving different use cases and performance characteristics. Understanding these collections is crucial for effective programming in Scala.</trait></trait></trait></trait></trait></trait></trait></trait></trait></trait></trait></trait>



# SCALA COLLECTIONS ÜBERBLICK

## scala.collection

### Grundlegende Unterschiede zu Java Collections
- Scala Collections unterscheiden sich grundlegend von Java Collections.
- Sie sind standardmäßig unveränderlich (immutable).
- Bieten eine einheitliche API.
- Unterstützen funktionale Operationen wie `filter`, `map` oder `fold` direkt (d.h. eine Umwandlung in Streams wie in Java ist für derartige Berechnungen nicht erforderlich).
- Zusätzlich erlaubt Scala einfache Parallelisierung und eine klare Trennung zwischen mutable und immutable Collections.

### Collection Traits
| Trait       | Description |
|-------------|-------------|
| **Iterable** | Basis-Trait für alle Sammlungen. |
| **Set**      | Eine Sammlung von einzigartigen Elementen. |
| **Map**      | Eine Sammlung von Schlüssel-Wert-Paaren. |
| **SortedSet**| Ein Set, das die Elemente in sortierter Reihenfolge hält. |
| **SortedMap**| Eine Map, die die Schlüssel in sortierter Reihenfolge hält. |
| **BitSet**   | Eine Sammlung von Bits. |
| **Seq**      | Eine Sequenz von Elementen. |
| **IndexedSeq** | Eine Sequenz, die schnellen Zugriff auf Elemente ermöglicht. |
| **LinearSeq** | Eine Sequenz, die eine lineare Struktur hat. |

### Pakete
Die meisten Collections werden durch Pakete `scala.collection.immutable` und `scala.collection.mutable` zur Verfügung gestellt. Collections aus `scala.collection` sind lediglich Traits, welche Supertypen ihrer immutablen und mutablen Gegenstücke sind.

----

PROGRAMMIEREN II | 2026 | KAPITEL 5



# SCALA COLLECTIONS ÜBERBLICK

## scala.collection.immutable

### Iterable
```scala
trait Iterable
```
Eine **immutable Collection** kann nicht aktualisiert werden, d.h. Elemente können weder verändert, noch hinzugefügt oder entfernt werden.

| **Set**       | **Map**       |
|---------------|---------------|
| `&#x3C;<trait>>`   | `&#x3C;<trait>>`   |
| HashSet       | HashMap       |
| ListSet       | SortedMap     |
| SortedSet     | SeqMap        |
| TreeSet       | ListMap       |
| BitSet        | VectorMap     |

Operationen wie Hinzufügen, Entfernen oder Modifizieren von Elementen werden stattdessen durch die Erzeugung einer neuen Collection simuliert.

Die ursprüngliche Collection bleibt unverändert, wodurch Nebenläufigkeit vereinfacht und Seiteneffekte vermieden werden.

### Seq
```scala
trait Seq
```
| **IndexedSeq** | **LinearSeq** |
|----------------|----------------|
| `&#x3C;<trait>>`    | `&#x3C;<trait>>`    |
| Vector         | ArraySeq       |
| Numeric        | String         |
| Range          | List           |
| LazyList       | Queue          |

----

PROGRAMMIEREN II | 2026 | KAPITEL 5    42</trait></trait></trait></trait>



# SCALA COLLECTIONS ÜBERBLICK

## scala.collection.mutable

### Iterable
```scala
trait Iterable[A] {
def iterator: Iterator[A]
}
```

### Set
```scala
trait Set[A] extends Iterable[A] {
// Set specific methods
}
```

#### Implementations of Set
- **HashSet**
- **LinkedHashSet**
- **SortedSet**
- **BitSet**

### Map
```scala
trait Map[K, V] extends Iterable[(K, V)] {
// Map specific methods
}
```

#### Implementations of Map
- **HashMap**
- **WeakHashMap**
- **ListMap**
- **TreeMap**
- **MultiMap**
- **SeqMap**

### Mutable Collections
Eine **mutable Collection** kann aktualisiert werden, d.h. Elemente der Collection können verändert werden oder es können neue Elemente der Collection hinzugefügt oder bestehende von ihr entfernt werden.

#### Examples of Mutable Collections
- **StringBuilder**
- **ArraySeq**
- **ArrayDeque**
- **ArrayBuffer**
- **ListBuffer**
- **Stack**
- **Queue**

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5

### Summary
In this chapter, we explored the various mutable collections available in Scala, including their traits and implementations. Mutable collections allow for dynamic changes, making them versatile for various programming needs.



# SCALA COLLECTIONS

## LISTEN

```scala
val list = List(1, 2, 3)

// Zugriff  // 1
list.head
list.tail   // List(2, 3)

// Transformation
val doubled = list.map(_ * 2) // List(2, 4, 6)
val list = 1 :: 2 :: 3 :: Nil // entspricht List(1, 2, 3)
```

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**    44



# SCALA COLLECTIONS

```scala
val list = List(1, 2, 3)

// Zugriff                     // 1
list.head                     // List(2, 3)
list.tail
```

```scala
// Transformation
val doubled = list.map(_ * 2) // List(2, 4, 6)
val list = 1 :: 2 :: 3 :: Nil // entspricht List(1, 2, 3)
```

Die List in Scala ist eine immutable, kovariante, linear verkettete Datenstruktur, die oft als Standard für sequentielle Daten verwendet wird.

- Effizienter Zugriff auf das erste Element mit `head` und den Rest mit `tail`.
- Zugriff auf das erste Element ist schnell (O(1)), aber der Zugriff auf das n-te Element ist langsam (O(n)).
- Unterstützt Methoden wie `map`, `filter`, `fold`, `flatMap`, etc.
- Konstruktion über Kopf und Rest der Liste mit dem Kons-Operator (`x::xs`).

----

PROGRAMMIEREN II | 2026 | KAPITEL 5



# SCALA COLLECTIONS: DIE LIST API

## PROGRAMMIEREN II | 2026 | KAPITEL 5

### Einführung in die List API

In Scala ist die `List` eine der grundlegenden Datenstrukturen, die eine sequenzielle Sammlung von Elementen darstellt. Sie ist unveränderlich (immutable), was bedeutet, dass einmal erstellte Listen nicht mehr verändert werden können. Stattdessen werden bei jeder Modifikation neue Listen erstellt.

### Grundlegende Eigenschaften von Listen

- **Unveränderlichkeit**: Listen können nicht verändert werden, was zu sichererem und vorhersagbarem Code führt.
- **Typensicherheit**: Listen sind typisiert, was bedeutet, dass sie nur Elemente eines bestimmten Typs enthalten können.
- **Verkettung**: Listen können einfach verkettet werden, um neue Listen zu erstellen.

### Wichtige Methoden der List API

Hier sind einige der häufigsten Methoden, die Sie mit Listen verwenden können:

| Methode               | Beschreibung                                           |
|----------------------|-------------------------------------------------------|
| `head`               | Gibt das erste Element der Liste zurück.              |
| `tail`               | Gibt die Liste ohne das erste Element zurück.         |
| `isEmpty`            | Überprüft, ob die Liste leer ist.                     |
| `length`             | Gibt die Anzahl der Elemente in der Liste zurück.     |
| `map`                | Wendet eine Funktion auf jedes Element der Liste an.  |
| `filter`             | Gibt eine neue Liste mit Elementen zurück, die ein Kriterium erfüllen. |
| `foldLeft`          | Reduziert die Liste auf einen einzelnen Wert, indem eine Funktion von links angewendet wird. |

### Beispiel: Erstellen und Verwenden von Listen

```scala
// Erstellen einer Liste
val zahlen = List(1, 2, 3, 4, 5)

// Zugriff auf das erste Element
val erstesElement = zahlen.head

// Erstellen einer neuen Liste mit map
val quadrierteZahlen = zahlen.map(x => x * x)

// Filtern der Liste
val geradeZahlen = zahlen.filter(x => x % 2 == 0)
```

### Mathematische Operationen mit Listen

Listen können auch für mathematische Operationen verwendet werden. Zum Beispiel können Sie die Summe aller Elemente in einer Liste berechnen:

```scala
val summe = zahlen.foldLeft(0)(_ + _)
```

### Fazit

Die `List` API in Scala bietet eine leistungsstarke und flexible Möglichkeit, mit sequenziellen Daten umzugehen. Durch die Verwendung von unveränderlichen Listen können Sie sicherstellen, dass Ihr Code weniger fehleranfällig ist und einfacher zu verstehen ist.

Für weitere Informationen und eine vollständige Dokumentation besuchen Sie bitte die Scala List API.



# SCALA COLLECTIONS

```scala
val catalog: List[Product] = List(
Product("Laptop", true, 89900, ELECTRONICS),
Product("T-Shirt", true, 2499, FASHION),
Product("Kochbuch", true, 1899, BOOKS),
Product("Smartphone", false, 69900, ELECTRONICS),
Product("Bio-Honig", true, 799, FOOD),
Product("Bluetooth-Lautsprecher", true, 4599, ELECTRONICS),
Product("Sneakers", false, 5999, FASHION),
Product("USB-C Kabel", true, 999, ELECTRONICS),
Product("Leder-Geldbörse", true, 3999, FASHION),
Product("Romanbestseller", true, 1499, BOOKS),
Product("Kaffeemaschine", true, 6999, ELECTRONICS),
Product("Fitness-Tracker", true, 3499, ELECTRONICS),
Product("Müsli-Riegel 12erPack", true, 299, FOOD),
Product("Gaming-Maus", true, 4999, ELECTRONICS),
Product("Designer-Schal", false, 6999, FASHION),
Product("USB-Stick 128GB", true, 1299, ELECTRONICS),
Product("Tee-Geschenkset", true, 1799, FOOD),
Product("Smartwatch", true, 7999, ELECTRONICS),
Product("Winterjacke", false, 12999, FASHION),
Product("Thriller-Hörbuch", true, 999, BOOKS),
Product("Espressokocher", true, 3499, FOOD),
Product("Notebook-Rucksack", true, 4599, FASHION),
Product("Geschenkbox 'Italien'", true, 2499, FOOD),
Product("Bildband Architektur", true, 2999, BOOKS),
Product("Wireless Charger", true, 2399, ELECTRONICS)
)
```

## Category Definition

```scala
sealed trait Category
case object ELECTRONICS extends Category
case object FASHION extends Category
case object BOOKS extends Category
case object FOOD extends Category
case object OTHER extends Category
```

## Product Class Definition

```scala
case class Product(
name: String,
available: Boolean,
price: Int, // Preis in Eurocent
category: Category
) {
override def toString: String =
s"$name (${price / 100.0} €)"
}
```

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# SCALA COLLECTIONS

## Lambda Expressions

### Example Code in Scala

```scala
val productNames: List[String] = catalog
.filter(p => p.available &#x26;&#x26; p.price &#x3C; 5000)
.sortBy(_.price)
.map(_.name)

println("Verfügbare Produkte unter 50 €:")
productNames.foreach(println)
```

### Example Code in Java Streams

```java
List<string> productNames = catalog.stream()
.filter(p -> p.isAvailable() &#x26;&#x26; p.getPrice() &#x3C; 5000)
.sorted(Comparator.comparing(Product::getPrice))
.map(Product::getName)
.collect(Collectors.toList());

System.out.println("Verfügbare Produkte unter 50 € (Streams):");
productNames.forEach(System.out::println);
```

### Explanation

- **Intermediate Operations**: `filter`, `sorted`, `map`
- **Terminal Operation**: `collect` (in Java) and `foreach` (in Scala)

----

### Summary

In both Scala and Java, we can use functional programming techniques to filter, sort, and map collections effectively. The examples above demonstrate how to retrieve product names that are available and under a certain price threshold.</string>



# SCALA COLLECTIONS

## LISTEN – EAGER ODER LAZY?

```scala
val productNames: List[String] = catalog
.map(s => { println(s"vor filter: $s"); s })
.filter(p => p.available &#x26;&#x26; p.price &#x3C; 5000)
.map(s => { println(s"vor sortBy: $s"); s })
.sortBy(_.price)
.map(s => { println(s"vor map: $s"); s })
.map(_.name)
```

----

### PROGRAMMIEREN II | 2026 | KAPITEL 5    49



# SCALA COLLECTIONS

## LIST VS LISTBUFFER

### LIST
```scala
val products = List("T-Shirt", "Kochbuch", "Smartwatch")
products += "Bluetooth-Lautsprecher" // This will not compile, as List is immutable
products(0) = "USB-Stick" // This will not compile, as List is immutable
val updated = "USB-Stick" :: products.tail // Creates a new List
```

### LISTBUFFER
```scala
import scala.collection.mutable.ListBuffer

val buffer = ListBuffer("T-Shirt", "Kochbuch", "Smartwatch")
buffer += "Bluetooth-Lautsprecher" // This works, as ListBuffer is mutable
buffer(0) = "USB-Stick" // This works, as ListBuffer is mutable
buffer.remove(1) // This works, as ListBuffer is mutable

println(buffer) // Prints the contents of the buffer
```

----

**Note:** In Scala, `List` is immutable, meaning once it is created, it cannot be changed. On the other hand, `ListBuffer` is mutable, allowing for modifications such as adding, updating, or removing elements.



# SCALA COLLECTIONS

## LIST VS LISTBUFFER

### LIST
```scala
val products = List("T-Shirt", "Kochbuch", "Smartwatch")
products += "Bluetooth-Lautsprecher" // This will not compile
products(0) = "USB-Stick" // This will not compile
products.remove(1) // This will not compile
val updated = "USB-Stick" :: products.tail
```

- **List ist unveränderlich**:
- Methoden wie `+=`, `remove`, `update` gibt es nicht.
- Änderungen erzeugen neue Listen, z.B. mit `::`.

### LISTBUFFER
- **ListBuffer ist veränderlich**:
- Methoden wie `+=`, `remove`, `update` sind verfügbar.
- Änderungen erfolgen in-place, ohne eine neue Liste zu erzeugen.

### Beispiel für ListBuffer
```scala
import scala.collection.mutable.ListBuffer

val productsBuffer = ListBuffer("T-Shirt", "Kochbuch", "Smartwatch")
productsBuffer += "Bluetooth-Lautsprecher" // This works
productsBuffer(0) = "USB-Stick" // This works
productsBuffer.remove(1) // This works
```

### Zusammenfassung
- Verwenden Sie `List`, wenn Sie eine unveränderliche Sammlung benötigen.
- Verwenden Sie `ListBuffer`, wenn Sie eine veränderliche Sammlung benötigen.



# SCALA COLLECTIONS

## LIST VS LISTBUFFER

`ListBuffer` ist eine veränderliche Liste, die für das effiziente schrittweise Erzeugen und Ändern von Listen verwendet wird. Sie erlaubt das Anhängen, Einfügen, Aktualisieren und Löschen von Elementen in-place. `ListBuffer` ist in Bezug auf den Typparameter A invariant.

### LISTBUFFER

```scala
import scala.collection.mutable.ListBuffer

val buffer = ListBuffer("T-Shirt", "Kochbuch", "Smartwatch")

buffer += "Bluetooth-Lautsprecher"
buffer(0) = "USB-Stick"
buffer.remove(1)

println(buffer)
```

PROGRAMMIEREN II | 2026 | KAPITEL 5 52



# SCALA COLLECTIONS

## FOLD UND REDUCE

### FOLDLEFT UND FOLDRIGHT
```scala
val totalPriceWithBase = catalog.map(_.price).foldLeft(100)(_ + _)
val allNamesRight = catalog.map(_.name).foldRight("")((name, acc) => name + " " + acc)
```

### REDUCELEFT UND REDUCERIGHT
```scala
val totalPrice = catalog.map(_.price).reduceLeft(_ + _)
val maxPrice = catalog.map(_.price).reduceRight((a, b) => if (a > b) a else b)
```

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5    53



# SCALA COLLECTIONS

## FOLD UND REDUCE

### FOLDLEFT UND FOLDRIGHT
```scala
val totalPriceWithBase = catalog.map(_.price).foldLeft(100)(_ + _)
val allNamesRight = catalog.map(_.name).foldRight("")((name, acc) => name + " " + acc)
```

### REDUCELEFT UND REDUCERIGHT
```scala
val totalPrice = catalog.map(_.price).reduceLeft(_ + _)
val maxPrice = catalog.map(_.price).reduceRight((a, b) => if (a > b) a else b)
```

Fold und Reduce verarbeiten alle Elemente einer Liste sequentiell zu einem einzelnen Ergebnis (ähnlich wie reduce bei Java Streams).

- **Fold** ist sicherer, da es einen Startwert verlangt.
- **Reduce** ist kompakter, kann aber bei leeren Listen fehlschlagen.
- Bei **foldLeft** und **reduceLeft** erfolgt die Verarbeitung von links nach rechts.
- Bei **foldRight** und **reduceRight** erfolgt die Verarbeitung von rechts nach links.
- **Fold** und **reduce** sind höherabstrahierte Varianten, die bei `List` wie `foldLeft` und `reduceLeft` arbeiten, aber bei anderen Collections nicht zwingend dieselbe Richtung haben.
- In Java entspricht `reduce(identity, BinaryOperator)` der `foldLeft`-Variante in Scala.

----

PROGRAMMIEREN II | 2026 | KAPITEL 5



# SCALA COLLECTIONS

## FOLD AND REDUCE

### FOLD LEFT and FOLD RIGHT

In Scala, the `foldLeft` and `foldRight` methods are used to reduce a collection to a single value by applying a binary operation.

#### Example of `foldLeft`

```scala
val numbers = List(1, 2, 3, 4)
val sum = numbers.foldLeft(0)((acc, num) => acc + num)
println(sum) // Output: 10
```

#### Example of `foldRight`

```scala
val numbers = List(1, 2, 3, 4)
val sum = numbers.foldRight(0)((num, acc) => acc + num)
println(sum) // Output: 10
```

### Comparison of `foldLeft` and `foldRight`

| Feature          | foldLeft                     | foldRight                    |
|------------------|------------------------------|------------------------------|
| Order of Operation | Left to Right               | Right to Left                |
| Accumulator      | Starts with the initial value | Starts with the initial value |
| Performance      | Generally more efficient for large collections | Can be less efficient due to stack usage |

### Mathematical Representation

The operation can be represented mathematically as follows:

- For `foldLeft`:
\[
f(a_0, f(a_1, f(a_2, \ldots f(a_{n-1}, a_n)))
\]

- For `foldRight`:
\[
f(f(a_0, a_1), f(a_2, \ldots f(a_{n-1}, a_n)))
\]

### Example Data

| Item Price | Item Name |
|------------|-----------|
| 89900      | Item A   |
| 2499       | Item B   |
| 1899       | Item C   |
| 69900      | Item D   |
| 4599       | Item E   |
| 2999       | Item F   |
| 2399       | Item G   |

### Conclusion

Understanding `foldLeft` and `foldRight` is crucial for functional programming in Scala, as they allow for powerful data manipulation and aggregation techniques.



# SCALA COLLECTIONS

## FOLD UND REDUCE – VERHALTEN BEI NICHT-ASSOZIATIVEN FUNKTIONEN

```scala
val names = catalog.take(3).map(_.name)
val left = names.foldLeft("BEGIN")((acc, name) => s"($acc + $name)")
val right = names.foldRight("BEGIN")((name, acc) => s"($name + $acc)")
println("foldLeft: " + left)
println("foldRight: " + right)
```

```scala
val prices = catalog.take(4).map(_.price)

val subLeft = prices.reduceLeft((a, b) => a - b)
val subRight = prices.reduceRight((a, b) => a - b)

println("reduceLeft: " + subLeft)
println("reduceRight: " + subRight)
```

----

PROGRAMMIEREN II | 2026 | KAPITEL 5    56



# SCALA COLLECTIONS

## LAZY LIST AND VIEW

```scala
val productIds: LazyList[Int] = LazyList.from(1000)

val nextThree = productIds
.filter(_ % 2 == 0)
.map(id => s"YAos-$id")
.take(3)
.toList

println(nextThree)
```

```scala
val productView = catalog.view
.filter(_.available)
.map(p => {
println(s"Mapping: ${p.name}")
p.name.toUpperCase
})

println("Vor foreach: keine Verarbeitung")
productView.foreach(println)
```

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**    57



# Scala Collections: LazyList and View

```scala
val productIds: LazyList[Int] = LazyList.from(1000)

val nextThree = productIds
.filter(_ % 2 == 0)
.map(id => s"YAos-$id")
.take(3)
.toList

println(nextThree)
```

In contrast to Java Streams, transformer methods on Scala Collections are not lazy but eager. A `LazyList` is an immutable, potentially infinite sequence of elements, where the elements are computed only when needed (lazy).

Through caching, each element is computed at most once. A `LazyList` computes only as many elements as necessary and is often used for generating elements. It supports all standard operations such as `map`, `filter`, `take`, etc.

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**    58



# SCALA COLLECTIONS

## LAZY LIST AND VIEW

A **View** is a lazy semantic representation of a Collection, where transformations such as `map`, `filter`, `flatMap`, etc., are not executed immediately but are evaluated only upon access. The underlying Collection remains unchanged when executing the transformations. This is useful for expensive transformations that may not be fully needed.

### Example Code

```scala
val productView = catalog.view
.filter(_.available)
.map(p => {
println(s"Mapping: ${p.name}")
p.name.toUpperCase
})

println("Vor foreach: keine Verarbeitung")
productView.foreach(println)
```

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# SCALA COLLECTIONS ÜBERPRÜFUNG
## LAZYLIST UND VIEW – DER LAZINESS

### LazyList Beispiel

```scala
val productIds: LazyList[Int] = LazyList.from(1000)

val nextThree = productIds
.map(s => { println(s"vor filter: $s"); s })
.filter(_ % 2 == 0)
.map(s => { println(s"vor map: $s"); s })
.map(id => s"YAoS-$id")
.map(s => { println(s"vor take: $s"); s })
.take(3)
.map(s => { println(s"vor toList: $s"); s })
.toList
```

### View Beispiel

```scala
val productView = catalog
.map(s => { println(s"vor view: $s"); s })
.view
.map(s => { println(s"vor filter: $s"); s })
.filter(_.available)
.map(s => { println(s"vor map: $s"); s })
.map(p => {
println(s"Mapping: ${p.name}")
p.name.toUpperCase
})

println("Vor foreach: keine Verarbeitung")
productView.foreach(println)
```

### Anmerkungen
- In der ersten Code-Sektion wird eine `LazyList` verwendet, die Elemente nur bei Bedarf generiert. Die Ausgaben zeigen, wann jedes Element verarbeitet wird.
- In der zweiten Code-Sektion wird eine `view` verwendet, die eine nicht-eager Verarbeitung ermöglicht, was bedeutet, dass die Elemente erst verarbeitet werden, wenn sie tatsächlich benötigt werden.



# MONADEN

## MOTIVATION: FUNKTIONEN MIT SEITENEFFEKTEN

```scala
import scala.io.StdIn.readLine // Für die folgenden Beispiele erforderlich

val readPrice: () => Double = () => {
println("Enter base price:")
readLine().toDouble
}

val applyDiscount: Double => Double = basePrice => {
println("Enter discount in %:")
val discount = readLine().toDouble
basePrice - (basePrice * discount / 100)
}

val applyVAT: Double => Double = priceWithoutVAT => {
println("Enter VAT in %:")
val vat = readLine().toDouble
priceWithoutVAT + (priceWithoutVAT * vat / 100)
}

val price = readPrice()
val discounted = applyDiscount(price)
val finalPrice = applyVAT(discounted)

println(s"Final price: $finalPrice")
```

----

PROGRAMMIEREN II | 2026 | KAPITEL 5    61



# MONADEN

## WAS IST EIN KONTEXT?

Ein Kontext ist ein Wert, der in einem bestimmten Rahmen oder einer bestimmten Umgebung existiert. In der Programmierung bezieht sich der Kontext oft auf die Umgebung, in der ein Wert oder eine Funktion ausgeführt wird.

### Wert in einem Kontext

| Wert       | Kontext     |
|------------|-------------|
| 3          | 3           |
| Wert      | einem       |

## PROGRAMMIEREN II | 2026 | KAPITEL 5

62



# MONADEN

## WAS IST EIN KONTEXT?

Ein *Kontext* ist eine strukturierte Hülle, in der ein Wert liegt, und die bestimmte Operationen auf diesem Wert erlaubt, aber nicht direkt. Der Kontext sagt: "Ich habe den Wert A, aber Du bekommst ihn nicht direkt. Wenn Du etwas damit tun willst, musst Du meine Regeln beachten." Werte werden häufig in Kontexte verpackt, z.B. um mit Fehlern, Seiteneffekten, Nebenläufigkeit oder Abwesenheit umzugehen.

| Wert in einem Kontext | Kontext-Typ      | Beschreibung                     | Beispielwert                  |
|-----------------------|------------------|----------------------------------|-------------------------------|
|                       | Option[A]        | Wert vorhanden oder nicht        | Some(42), None                |
|                       | List[A]          | Null oder mehrere Werte          | List(1,2,3)                   |
|                       | Future[A]        | Wert kommt irgendwann            | Future.successful("ok")       |
|                       | Either[E, A]     | Entweder Fehler oder Wert        | Right(99), Left("Fehler")     |
|                       | Try[A]           | Erfolg oder Exception            | Success(7), Failure(...)       |

----

PROGRAMMIEREN II | 2026 | KAPITEL 5    63



# MONADEN

## WIE ERZEUGT MAN EINEN KONTEXT?

### ERZEUGUNG MIT EINEM KONSTRUKTOR

```scala
val kontext = Some(3)
```
Wert in einem Kontext

### ERZEUGUNG MIT EINER FUNKTION

```scala
val readPrice: () => Option[Double] = () => {
println("Enter base price:")
readLine().toDoubleOption
}
```
Wert in einem Kontext

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5    64



# MONADEN

## EIN KONTEXT ALS ARGUMENT EINER FUNKTION FUNKTIONIERT NICHT

### Anwendung einer Funktion auf einem Argument (=Wert)

```plaintext
f(3)  f(   )
```

### Anwendung einer Funktion auf einem Argument (=Kontext)

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5

65



# MONADEN

## MAP BERECHNET AUSSERHALB DES KONTEXT

```scala
mapB: Option[B]
```

### Beispiel

```scala
3 Int => Int = x => x + 1
```

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5

66



# MONADEN

## MAP BERECHNET AUSSERHALB DES KONTEXT

```scala
mapB: Option[B]
```

```scala
3 Int => Int = x => x + 1
```

`mapB: F[B]` wendet eine Funktion `A => B` auf den Inhalt eines Kontexts `F[A]` an und gibt einen neuen Kontext `F[B]` zurück.

### Problem

`map` holt den Wert aus dem Kontext, führt eine Berechnung außerhalb des Kontextes durch und bettet das Ergebnis in einen Kontext ein. Aber die Berechnung selbst unterliegt nicht dem Kontext.

- Fehlerhafte Daten
- Frühzeitiges Abbrechen
- Logging wird durch `f` nicht behandelt

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5

67



# MONADEN

## MAP BERECHNET AUSSERHALB DES KONTEXT

```scala
val readPrice: () => Option[Double] = () => {
println("Enter base price:")
readLine().toDoubleOption
}

val applyDiscount: Double => Double = basePrice => {
println("Enter discount in %:")
val discount = readLine().toDouble
basePrice - (basePrice * discount / 100)
}

val applyVAT: Double => Double = priceWithoutVAT => {
println("Enter VAT in %:")
val vat = readLine().toDouble
priceWithoutVAT + (priceWithoutVAT * vat / 100)
}

readPrice()
.map(applyDiscount)
.map(applyVAT)
```

----

PROGRAMMIEREN II | 2026 | KAPITEL 5                       68



# MONADEN

## MAP ERZEUGT VERSCHACHTELTE KONTEXTE

```scala
mapB: Option[B]
```

```scala
3 Int => Option[Int] = x => Some(x + 1)
```

### Verschachtelter Kontext

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5

69



# MONADEN

## MAP ERZEUGT VERSCHACHTELTE KONTEXTE

```scala
mapB: Option[B]
```

```scala
3 Int => Option[Int] = x => Some(x + 1)
```

### Verschachtelter Kontext

Damit die an `map` übergebene Funktion `f` Berechnungen im Kontext durchführt, kann man `f` derart definieren, dass sie selber einen Kontext zurückgibt: `A => F[B]`.

**Problem:** Wenn die Funktion selbst einen Kontext zurückgibt, entsteht ein verschachtelter Kontext.

----

PROGRAMMIEREN II | 2026 | KAPITEL 5    70



# MONADEN
## MAP ERZEUGT VERSCHACHTELTE KONTEXTE

```scala
val readPrice: () => Option[Double] = () => {
println("Enter base price:")
readLine().toDoubleOption
}

val applyDiscount: Double => Option[Double] = basePrice => {
println("Enter discount in %:")
readLine().toDoubleOption.map { discount =>
basePrice - (basePrice * discount / 100)
}
}

val applyVAT: Double => Option[Double] = priceWithoutVAT => {
println("Enter VAT in %:")
readLine().toDoubleOption.map { vat =>
priceWithoutVAT + (priceWithoutVAT * vat / 100)
}
}

readPrice()
.map(applyDiscount)
.map(_.map(applyVAT))
```

## PROGRAMMIEREN II | 2026 | KAPITEL 5    71



# MONADEN

## FLATMAP HÄLT DEN KONTEXT "FLACH"

### Definition

```scala
flatMapB: Option[B]
```

### Beispiel

```scala
val increment: Int => Option[Int] = x => Some(x + 1)
```

### Erklärung

Die Funktion `flatMap` ermöglicht es, eine Funktion auf den Wert innerhalb einer Monade anzuwenden und das Ergebnis in der gleichen Monade zu behalten. Dies hilft, den Kontext "flach" zu halten, indem es die Verschachtelung von Monaden vermeidet.

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5

### Seite 72

----

Bitte beachten Sie, dass die oben genannten Konzepte und Beispiele Teil eines größeren Themas in der Programmierung sind, das sich mit Monaden und deren Verwendung in funktionalen Programmiersprachen beschäftigt.



# MONADEN

## FLATMAP HÄLT DEN KONTEXT "FLACH"

```scala
flatMapB: Option[B]
```

### Beispiel

```scala
val f: Int => Option[Int] = x => Some(x + 1)
```

`flatMapB: G[B]` führt eine Funktion aus, die einen Wert `A` in einen neuen Kontext `F[B]` verpackt und flacht den doppelten Kontext zu einem einzelnen `G[B]` ab.

In manchen Implementierungen akzeptiert `f` oft allgemeinere Typen (z.B. `IterableOnce[B]`) für Rückgabeparameter, aber das Ergebnis bleibt im ursprünglich Kontext (z.B. `List`). In vielen Implementierungen gilt jedoch `F[B] = G[B]`.

`flatMap` vermeidet die bei `map` auftretende Einbettung von Kontexten, indem der Rückgabetyp des Kontextes der Funktion `f` und von `flatMap` identisch sind.

`flatMap` wendet eine Funktion an, die von `A` in einen Kontext verpackt und verhindert das doppelte Verpacken.

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# MONADEN

## FLATMAP HÄLT DEN KONTEXT "FLACH"

```scala
val readPrice: () => Option[Double] = () => {
println("Enter base price:")
readLine().toDoubleOption
}

val applyDiscount: Double => Option[Double] = basePrice => {
println("Enter discount in %:")
readLine().toDoubleOption.map { discount =>
basePrice - (basePrice * discount / 100)
}
}

val applyVAT: Double => Option[Double] = priceWithoutVAT => {
println("Enter VAT in %:")
readLine().toDoubleOption.map { vat =>
priceWithoutVAT + (priceWithoutVAT * vat / 100)
}
}

readPrice()
.flatMap(applyDiscount)
.flatMap(applyVAT) match {
case Some(finalPrice) => println(s"Final price: $finalPrice")
case None => println("Invalid input")
}
```

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5

74



# MONADEN

## WAS SIND MONADEN?

Eine **Monade** ist ein Typ mit:
- einem Konstruktor, der einen Wert in einen Kontext einpackt (z.B. Some, List,...),
- einer Methode `flatMap`, um Operationen im Kontext zu verketten und
- den drei folgenden Gesetzen, die sicherstellen, dass sich diese Verkettung zuverlässig verhält.

Der Begriff Monade stammt aus der Philosophie: Monaden sind atomare, unteilbare Bausteine der Realität (nach Gottfried Wilhelm Leibniz).

### LINKE IDENTITÄT
Wenn man einen Wert mit dem Konstruktor in die Monade packt und ihn sofort per `flatMap` an eine Funktion `f` übergibt, dann ist das dasselbe wie `f` direkt auf den Wert anzuwenden.

### RECHTE IDENTITÄT
Wenn man einen Monadenwert per `flatMap` an den Konstruktor übergibt, bekommt man denselben Monadenwert zurück.

### ASSOZIATIVITÄT
Die Reihenfolge der Anwendung mehrerer Funktionen auf Monaden ist unabhängig davon, ob sie durch aufeinanderfolgende `flatMap`-Aufrufe oder durch verschachtelte `flatMap`-Aufrufe übergeben werden – das Endergebnis bleibt dasselbe.

----

PROGRAMMIEREN II | 2026 | KAPITEL 5



# MONADEN

## WAS SIND MONADEN?

### LINKE IDENTITÄT
```scala
val f: Int => Option[Int] = x => Some(x + 1)
val left = Some(3).flatMap(f)
val right = f(3)

left == right
```

### RECHTE IDENTITÄT
```scala
val m = Some(42)
val result = m.flatMap(x => Some(x))

result == m
```

### ASSOZIATIVITÄT
```scala
val f: Int => Option[Int] = x => Some(x + 1)
val g: Int => Option[Int] = x => Some(x * 2)
val m = Some(3)

val left = m.flatMap(f).flatMap(g)
val right = m.flatMap(x => f(x).flatMap(g))

left == right
```

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5    76



# MONADEN

## EITHER

The `Either[A, B]` type is used to represent a value that can be one of two possible types. It is commonly used for error handling in functional programming.

### Definition

```scala
val safeDivide: (Int, Int) => Either[String, Int] = (a, b) =>
if (b == 0)
Left("Division by zero is not allowed")
else
Right(a / b)
```

### Methods

- `isLeft: Boolean`
- `isRight: Boolean`
- `flatMap(...): Either[A, B]`

### Example Usage

```scala
val result = safeDivide(10, 0)
result match {
case Right(value) => println(s"Result: $value")
case Left(error) => println(s"Error: $error")
}
```

### Summary

- `Left[+A, +B]` represents an error or failure.
- `Right[+A, +B]` represents a successful computation.

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# MONADEN

## EITHER

```scala
Either[A, B]
```

```scala
val safeDivide: (Int, Int) => Either[String, Int] = (a, b) =>
if (b == 0)
Left("Division by zero is not allowed")
else
Right(a / b)
```

```scala
val result = safeDivide(10, 0)
result match {
case Right(value) => println(s"Result: $value")
case Left(error) => println(s"Error: $error")
}
```

### Left and Right

- `Left[+A, +B]`: Represents an error.
- `Right[+A, +B]`: Represents a successful result.

## Explanation

With `Option[A]`, it can be expressed that a value is missing by assigning `None`, but the reason for the absence cannot be specified.

`Either[A, B]` is a data type that contains either a value of type A or a value of type B.
- `Left(a)` conventionally represents an error.
- `Right(b)` conventionally represents a successful result.

`Either[A, B]` is another example of a monad that is immutable and covariant with respect to its type parameters A and B.

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# Monad and Either

## Code Implementation

```scala
val readPrice: () => Either[String, Double] = () => {
println("Enter base price:")
readLine().toDoubleOption.toRight("Invalid base price input")
}

val applyDiscount: Double => Either[String, Double] = basePrice => {
println("Enter discount in %:")
readLine().toDoubleOption
.toRight("Invalid discount input")
.map(discount => basePrice - (basePrice * discount / 100))
}

val applyVAT: Double => Either[String, Double] = priceWithoutVAT => {
println("Enter VAT in %:")
readLine().toDoubleOption
.toRight("Invalid VAT input")
.map(vat => priceWithoutVAT + (priceWithoutVAT * vat / 100))
}

val result = readPrice()
.flatMap(applyDiscount)
.flatMap(applyVAT)

result match {
case Right(finalPrice) => println(s"Final price: $finalPrice")
case Left(error) => println(s"Error: $error")
}
```

## Explanation

1. **readPrice**: This function prompts the user to enter a base price and returns it wrapped in an `Either`. If the input is invalid, it returns a `Left` with an error message.

2. **applyDiscount**: This function takes the base price and prompts the user for a discount percentage. It calculates the discounted price and returns it wrapped in an `Either`.

3. **applyVAT**: Similar to `applyDiscount`, this function takes the price without VAT and prompts for the VAT percentage, returning the final price with VAT included.

4. **Result Handling**: The final result is processed using pattern matching to either display the final price or an error message.

## Summary

This code demonstrates the use of `Either` to handle potential errors in user input while calculating a final price after applying a discount and VAT.



# MONADEN

## EITHER

```scala
val readPrice: () => Either[String, Double] = () => {
println("Enter base price:")
readLine().toDoubleOption.toRight("Invalid base price input")
}

val applyDiscount: Double => Either[String, Double] = basePrice => {
println("Enter discount in %:")
readLine().toDoubleOption
.toRight("Invalid discount input")
.map(discount => basePrice - (basePrice * discount / 100))
}

val applyVAT: Double => Either[String, Double] = priceWithoutVAT => {
println("Enter VAT in %:")
readLine().toDoubleOption
.toRight("Invalid VAT input")
.map(vat => priceWithoutVAT + (priceWithoutVAT * vat / 100))
}
```

### Erklärung

`toRight(leftValue)` wandelt eine Option in ein Either um.
- Wenn die Option `Some(value)` ist, dann wird sie zu `Right(value)` umgewandelt.
- Wenn die Option `None` ist, dann wird sie zu `Left(leftValue)` umgewandelt.

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# MONADISCHE OPERATIONEN AUF LISTEN

## Beispiel: T-Shirts generieren

Hier zeigen wir, wie man mit `map` und `flatMap` Listen von T-Shirts generieren kann.

### Mit `map`

```scala
val colors = List("rot", "grün", "blau")
val sizes = List("S", "M", "L", "xL")
val styles = List("Motiv", "Basic")

val tshirts = colors.map { color =>
sizes.map { size =>
styles.map { style =>
(color, size, style)
}
}
}
```

### Mit `flatMap`

```scala
val tshirts = colors.flatMap { color =>
sizes.flatMap { size =>
styles.map { style =>
(color, size, style)
}
}
}
```

## Erklärung

- **`map`**: Erzeugt eine Liste von Listen. Jede Farbe wird mit jeder Größe und jedem Stil kombiniert, was zu einer verschachtelten Struktur führt.
- **`flatMap`**: Flacht die Struktur ab und erzeugt eine flache Liste von T-Shirts, indem es die inneren Listen zusammenführt.

### Ergebnis

Beide Ansätze führen zu einer Liste von T-Shirts, jedoch ist das Ergebnis bei `flatMap` einfacher zu handhaben, da es eine flache Liste zurückgibt.



# MONADEN DESUGARING FÜR-COMPREHENSIONS

## SYNTAKTISCHER ZUCKER MIT FLATMAP

### 1. For-Comprehension

```scala
for {
color &#x3C;- colors
size &#x3C;- sizes
style &#x3C;- styles
} yield (color, size, style)
```

### 2. Entsprechende Verwendung von `flatMap`

```scala
val tshirts =
colors.flatMap { color =>
sizes.flatMap { size =>
styles.map { style =>
(color, size, style)
}
}
}
```

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5

82



# MONADEN DESUGARING FOR-COMPREHENSIONS

## MIT "SUGAR"                                  OHNE "SUGAR"

```scala
val nums = List(1, 2, 3)
for (n &#x3C;- nums) println(n * 2)
```

```scala
nums.foreach(n => println(n * 2))
```

```scala
val nums = List(1, 2, 3)
for (n &#x3C;- nums) yield n * 2
```

```scala
nums.map(n => n * 2)
```

```scala
val nums = List(1, 2, 3)
val doubled = for (n &#x3C;- nums) yield n * 2
```

```scala
val doubled = nums.map(n => n * 2)
```

```scala
val nums = List(1, 2, 3, 4)
for (n &#x3C;- nums if n % 2 == 0) yield n * 2
```

```scala
nums.filter(n => n % 2 == 0)
.map(n => n * 2)
```

----

PROGRAMMIEREN II | 2026 | KAPITEL 5                                            83



# MONADEN: DESUGARING FÜR FOR-COMPREHENSIONS

## MIT "SUGAR"                                                 | ## OHNE "SUGAR"
------------------------------------------------------------- | -------------------------------------------------------------
```scala
val nums = List(1, 2, 3)                                    | ```scala
for (n &#x3C;- nums) println(n * 2)                              | nums.foreach(n => println(n * 2))
```
```scala
val nums = List(1, 2, 3)                                     | ```scala
for (n &#x3C;- nums) yield n * 2                                  | nums.map(n => n * 2)
```
```scala
val nums = List(1, 2, 3)                                     | ```scala
val doubled = for (n &#x3C;- nums) yield n * 2                    | val doubled = nums.map(n => n * 2)
```

### Wiederholung aus Kapitel:
- for-Comprehension iteriert über Collections und andere "Traversable"-Typen, um einen Blockausdruck wiederholt auszuführen und/oder Ergebnisse zu transformieren.
- Der Generator `&#x3C;-` bindet jedes Element der Collection an eine Variable.
- Die Syntax `for (element &#x3C;- collection) yield Transformation` ist syntaktischer Zucker für eine Abbildung auf eine oder mehrere Transformer-Methoden der jeweiligen Collection.

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5    84



# MONADEN: DESUGARING FÜR-COMPREHENSIONS

## MIT "SUGAR"                                  OHNE "SUGAR"

```scala
val nums = List(1, 2, 3)
for (n &#x3C;- nums) println(n * 2)
```
```scala
nums.foreach(n => println(n * 2))
```

```scala
val nums = List(1, 2, 3)
for (n &#x3C;- nums) yield n * 2
```
```scala
nums.map(n => n * 2)
```

```scala
val nums = List(1, 2, 3)
val doubled = for (n &#x3C;- nums) yield n * 2
```
```scala
val doubled = nums.map(n => n * 2)
```

Der Rumpf der for-Comprehension wird durch die Methode `forEach` der jeweiligen Collection implementiert. `forEach` bekommt als Argument eine Funktion, die auf jedes Element angewendet wird und keinen Wert zurückliefert, also Seiteneffekte erzeugt.

`yield` gibt für jedes Element das Ergebnis einer Abbildungsfunktion zurück und sammelt diese in einer Collection. `yield` wird durch eine `map`-Methode auf der jeweiligen Collection implementiert, die als Argument die Abbildungsfunktion übergeben bekommt.

----

## PROGRAMMIEREN II | 2026 | KAPITEL 5    85



# MONADEN: DESUGARING FÜR FOR-COMPREHENSIONS

Der `if-Guard` einer `for-Comprehension` wird durch eine `filter`-Methode implementiert, die als Argument das Filterkriterium, als eine Prädikat übergeben bekommt.

| MIT "SUGAR"                                      | OHNE "SUGAR"                                   |
|--------------------------------------------------|------------------------------------------------|
| ```scala                                         | ```scala                                       |
| val nums = List(1, 2, 3, 4)                      | val nums = List(1, 2, 3, 4)                   |
| for (n &#x3C;- nums if n % 2 == 0) yield n * 2       | nums.filter(n => n % 2 == 0)                  |
| ```                                              | .map(n => n * 2)                              |
|                                                  | ```                                            |

----

PROGRAMMIEREN II | 2026 | KAPITEL 5    86



# MONADEN DESUGARING FOR-COMPREHENSIONS

```scala
val readPrice: () => Either[String, Double] = () => {
println("Enter base price:")
readLine().toDoubleOption.toRight("Invalid base price input")
}

val applyDiscount: Double => Either[String, Double] = basePrice => {
println("Enter discount in %:")
readLine().toDoubleOption
.toRight("Invalid discount input")
.map(discount => basePrice - (basePrice * discount / 100))
}

val applyVAT: Double => Either[String, Double] = priceWithoutVAT => {
println("Enter VAT in %:")
readLine().toDoubleOption
.toRight("Invalid VAT input")
.map(vat => priceWithoutVAT + (priceWithoutVAT * vat / 100))
}
```

## MIT FLATMAP vs MIT FOR

### Using FlatMap

```scala
val result = readPrice()
.flatMap(applyDiscount)
.flatMap(applyVAT)

result match {
case Right(finalPrice) => println(s"Final price: $finalPrice")
case Left(error)       => println(s"Error: $error")
}
```

### Using For-Comprehension

```scala
val result = for {
base  &#x3C;- readPrice()
net   &#x3C;- applyDiscount(base)
gross &#x3C;- applyVAT(net)
} yield gross

result match {
case Right(finalPrice) => println(s"Final price: $finalPrice")
case Left(error)       => println(s"Error: $error")
}
```

----

**PROGRAMMIEREN II | 2026 | KAPITEL 5**



# VORLESUNG
## PROF. DR. AXEL KÜPPER
TU Berlin | T-Labs | Fachgebiet Service-centric Networking
Ernst-Reuter-Platz 1 | 10587 Berlin | Germany
axel.kuepper@tu-berlin.de
LinkedIn
TU Berlin

### ÜBUNGSLEITER
- YASSINE LAZREG
- CHRISTIAN RENÉ SECHTING

### TUTOREN
**PROGRAMMIEREN II**
- SAMA AMIN
- FIN JAKOB FREESE
- TENZIN-LHAM
- GELEGJAMTS
- PHILIPP TRILK
- PHILIP MARLOW

### TECHNISCHE UNIVERSITÄT BERLIN
**INET TLabs**

*Hinweis: Teile der Folien wurden mit Hilfe von ChatGPT erstellt*