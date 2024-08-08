import { useState, SetStateAction } from "react";

enum CropType {
    Strawberry,
    Tomato
}

type CounterComponentProps = {
    setCurrentView: React.Dispatch<SetStateAction<"home" | "counter">>
}

const CounterComponent: React.FC<CounterComponentProps> = ({setCurrentView}) => {
    const [count, setCount] = useState<number>(1);
    const [selectedCrop, setSelectedCrop] = useState<CropType>(CropType.Strawberry)

    const updateCount = () => {
        setCount(count * 2);
    }

    return (<div className="counter-component">
        <div className="counter-text">Current Count: </div>
        <div className="counter-value">{count}</div>
        <button onClick={updateCount}>Increase Count</button>
        <button onClick={() => setCurrentView("home")}>Home</button>
        </div>)
};

export default CounterComponent;