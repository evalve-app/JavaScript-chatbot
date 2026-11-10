# JavaScript Prototypes and Classes

## Explanation

Every JavaScript object has an internal link to another object called its **prototype**. When you read a property that the object does not have, JavaScript looks it up on the prototype, then on the prototype's prototype, and so on. This is the **prototype chain**, and it ends at `null`.

This is how arrays get methods like `map`: `[]` has no `map` property of its own; it finds `map` on `Array.prototype`.

The `class` syntax is a clearer way to write constructor functions and prototype methods. It does not change how inheritance works underneath.

## Examples

Prototypes directly:

```javascript
const animal = {
  speak() {
    return `${this.name} makes a sound`;
  },
};

const dog = Object.create(animal); // dog's prototype is animal
dog.name = 'Rex';

console.log(dog.speak());                             // Rex makes a sound
console.log(Object.getPrototypeOf(dog) === animal);   // true
console.log(Object.hasOwn(dog, 'speak'));             // false: inherited
```

Classes:

```javascript
class Animal {
  #sound = 'a sound'; // private field

  constructor(name) {
    this.name = name;
  }

  speak() {
    return `${this.name} makes ${this.#sound}`;
  }

  static create(name) {
    return new Animal(name);
  }
}

class Dog extends Animal {
  constructor(name, breed) {
    super(name); // must call super before using this
    this.breed = breed;
  }

  speak() {
    return `${super.speak()} (woof)`;
  }
}

const rex = new Dog('Rex', 'collie');
console.log(rex.speak());              // Rex makes a sound (woof)
console.log(rex instanceof Animal);    // true
console.log(typeof Animal);            // 'function'
```

Methods defined in a class body live on `Animal.prototype`, so all instances share one copy.

## Common Mistakes

- Forgetting `new` when creating an instance. Calling a class without `new` throws a `TypeError`.
- Using `this` before calling `super()` in a subclass constructor (a `ReferenceError`).
- Losing `this` when passing a method as a callback: `button.onclick = rex.speak`. Use an arrow function or `bind`.
- Modifying built-in prototypes like `Array.prototype`, which can break other code.

## Edge Cases

- Class declarations are hoisted but stay in the temporal dead zone until defined.
- Class bodies always run in strict mode.
- `Object.create(null)` makes an object with no prototype at all.
