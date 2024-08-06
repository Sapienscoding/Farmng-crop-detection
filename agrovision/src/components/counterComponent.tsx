import { useState } from "react";

enum CropType {
    Strawberry,
    Tomato
}

const CounterComponent = () => {
    const [count, setCount] = useState<number>(1);
    const [selectedCrop, setSelectedCrop] = useState<CropType>(CropType.Strawberry)

    const updateCount = () => {
        setCount(count * 2);
    }

    return (<div className="counter-component">
        <div className="counter-text">Current Count: </div>
        <div className="counter-value">{count}</div>
        <button onClick={updateCount}>Increase Count</button>
        </div>)
};

export default CounterComponent;