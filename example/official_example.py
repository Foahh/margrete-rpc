from __future__ import annotations

from margrete_rpc import (
    AirCrushOption,
    BeatChangeEvent,
    BpmEvent,
    Direction,
    ExAttr,
    Margrete,
    Note,
    TimelineSpeedEvent,
)

BAR_TICKS = 1920 * 4


def build_official_chart() -> list[Note]:
    notes: list[Note] = []

    # BAR 1
    # Taps
    notes.extend(
        [
            Note.tap(0, 0, 4),
            Note.tap(480, 4, 4),
            Note.tap(960, 8, 4),
            Note.tap(1440, 12, 4),
        ]
    )

    # ExTaps
    notes.extend(
        [
            Note.extap(1920, 0, 4, direction=Direction.UP),
            Note.extap(2400, 4, 4, direction=Direction.UP),
            Note.extap(2880, 8, 4, direction=Direction.UP),
            Note.extap(3360, 12, 4, direction=Direction.UP),
            Note.extap(3840, 0, 4, direction=Direction.UP),
            Note.extap(4080, 4, 4, direction=Direction.DOWN),
            Note.extap(4320, 8, 4, direction=Direction.CENTER),
            Note.extap(4560, 12, 4, direction=Direction.LEFT),
            Note.extap(4800, 0, 4, direction=Direction.RIGHT),
            Note.extap(5040, 4, 4, direction=Direction.ROTATE_LEFT),
            Note.extap(5280, 8, 4, direction=Direction.ROTATE_RIGHT),
            Note.extap(5520, 12, 4, direction=Direction.INOUT),
        ]
    )

    # Flicks
    notes.extend(
        [
            Note.flick(5760, 0, 4, direction=Direction.AUTO),
            Note.flick(6240, 4, 4, direction=Direction.AUTO),
            Note.flick(6720, 8, 4, direction=Direction.AUTO),
            Note.flick(7200, 12, 4, direction=Direction.AUTO),
        ]
    )

    # BAR 2
    # Flicks
    notes.extend(
        [
            Note.flick(7680, 0, 2, direction=Direction.RIGHT),
            Note.flick(7740, 2, 2, direction=Direction.RIGHT),
            Note.flick(7800, 4, 2, direction=Direction.RIGHT),
            Note.flick(7860, 6, 2, direction=Direction.RIGHT),
            Note.flick(7920, 8, 2, direction=Direction.RIGHT),
            Note.flick(7980, 10, 2, direction=Direction.RIGHT),
            Note.flick(8040, 12, 2, direction=Direction.RIGHT),
            Note.flick(8100, 14, 2, direction=Direction.RIGHT),
            Note.flick(8640, 14, 2, direction=Direction.LEFT),
            Note.flick(8700, 12, 2, direction=Direction.LEFT),
            Note.flick(8760, 10, 2, direction=Direction.LEFT),
            Note.flick(8820, 8, 2, direction=Direction.LEFT),
            Note.flick(8880, 6, 2, direction=Direction.LEFT),
            Note.flick(8940, 4, 2, direction=Direction.LEFT),
            Note.flick(9000, 2, 2, direction=Direction.LEFT),
            Note.flick(9060, 0, 2, direction=Direction.LEFT),
        ]
    )

    # Slides
    notes.extend(
        [
            Note.slide_begin(
                9600,
                0,
                4,
                children=[
                    Note.slide_end(10560, 12, 4),
                ],
            ),
            Note.slide_begin(
                11520,
                0,
                4,
                children=[
                    Note.slide_control(12000, 12, 4),
                    Note.slide_step(12480, 0, 4),
                    Note.slide_end(12960, 12, 4),
                ],
            ),
        ]
    )

    # Holds
    notes.append(
        Note.hold_begin(
            13440,
            6,
            4,
            children=[
                Note.hold_end(14400, 6, 4),
            ],
        )
    )

    # BAR 3
    # Taps
    notes.extend(
        [
            Note.tap(
                15360,
                4,
                8,
                children=[
                    Note.air(15360, 4, 8, direction=Direction.UP),
                ],
            ),
            Note.tap(
                15840,
                4,
                8,
                children=[
                    Note.air(15840, 4, 8, direction=Direction.UPLEFT),
                ],
            ),
            Note.tap(
                16320,
                4,
                8,
                children=[
                    Note.air(16320, 4, 8, direction=Direction.UPRIGHT),
                ],
            ),
            Note.tap(
                16800,
                4,
                8,
                children=[
                    Note.air(16800, 4, 8, direction=Direction.DOWN),
                ],
            ),
            Note.tap(
                17280,
                4,
                8,
                children=[
                    Note.air(17280, 4, 8, direction=Direction.DOWNLEFT),
                ],
            ),
            Note.tap(
                17760,
                4,
                8,
                children=[
                    Note.air(17760, 4, 8, direction=Direction.DOWNRIGHT),
                ],
            ),
            Note.tap(
                18240,
                4,
                8,
                children=[
                    Note.air(
                        18240, 4, 8, direction=Direction.UP, ex_attr=ExAttr.INVERT
                    ),
                ],
            ),
            Note.tap(
                18720,
                4,
                8,
                children=[
                    Note.air(
                        18720, 4, 8, direction=Direction.DOWN, ex_attr=ExAttr.INVERT
                    ),
                ],
            ),
            Note.tap(
                19200,
                4,
                8,
                children=[
                    Note.air(
                        19200,
                        4,
                        8,
                        direction=Direction.UP,
                        children=[
                            Note.air_hold_begin(
                                19200,
                                4,
                                8,
                                80,
                                children=[
                                    Note.air_hold_step(19680, 4, 8, 800),
                                    Note.air_hold_end(20160, 4, 8, 800),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            Note.tap(
                21120,
                4,
                8,
                children=[
                    Note.air(
                        21120,
                        4,
                        8,
                        direction=Direction.UP,
                        children=[
                            Note.air_slide_begin(
                                21120,
                                4,
                                8,
                                80,
                                children=[
                                    Note.air_slide_control(21600, 8, 8, 80),
                                    Note.air_slide_step(22080, 0, 8, 80),
                                    Note.air_slide_control(22200, 5, 8, 80),
                                    Note.air_slide_control(22320, 7, 8, 80),
                                    Note.air_slide_control(22440, 8, 8, 80),
                                    Note.air_slide_control(22680, 8, 8, 80),
                                    Note.air_slide_control(22800, 7, 8, 80),
                                    Note.air_slide_control(22920, 5, 8, 80),
                                    Note.air_slide_step(23040, 0, 8, 80),
                                    Note.air_slide_control(23160, 0, 8, 140),
                                    Note.air_slide_control(23280, 0, 8, 160),
                                    Note.air_slide_control(23400, 0, 8, 140),
                                    Note.air_slide_control(23520, 0, 8, 80),
                                    Note.air_slide_control(23640, 0, 8, 20),
                                    Note.air_slide_control(23760, 0, 8, 0),
                                    Note.air_slide_control(23880, 0, 8, 20),
                                    Note.air_slide_end(24000, 0, 8, 80),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )

    # BAR 4
    # Taps
    notes.extend(
        [
            Note.tap(
                24960,
                0,
                4,
                children=[
                    Note.air(
                        24960,
                        0,
                        4,
                        direction=Direction.UP,
                        children=[
                            Note.air_slide_begin(
                                24960,
                                0,
                                4,
                                0,
                                children=[
                                    Note.air_slide_control(25080, 1, 4, 80),
                                    Note.air_slide_control(25200, 2, 4, 120),
                                    Note.air_slide_control(25320, 3, 4, 140),
                                    Note.air_slide_control(25440, 4, 4, 150),
                                    Note.air_slide_control(25560, 5, 4, 150),
                                    Note.air_slide_control(25680, 6, 4, 120),
                                    Note.air_slide_control(25800, 7, 4, 80),
                                    Note.air_slide_end(25920, 8, 4, 10),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            Note.tap(
                24960,
                4,
                4,
                children=[
                    Note.air(
                        24960,
                        4,
                        4,
                        direction=Direction.UP,
                        children=[
                            Note.air_slide_begin(
                                24960,
                                4,
                                4,
                                0,
                                children=[
                                    Note.air_slide_control(25080, 5, 4, 80),
                                    Note.air_slide_control(25200, 6, 4, 120),
                                    Note.air_slide_control(25320, 7, 4, 140),
                                    Note.air_slide_control(25440, 8, 4, 150),
                                    Note.air_slide_control(25560, 9, 4, 150),
                                    Note.air_slide_control(25680, 10, 4, 120),
                                    Note.air_slide_control(25800, 11, 4, 80),
                                    Note.air_slide_end(25920, 12, 4, 10),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )

    # Air crushes
    notes.extend(
        [
            Note.air_crush_begin(
                26880,
                0,
                4,
                0,
                5,
                children=[
                    Note.air_crush_end(26890, 0, 4, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                27360,
                4,
                4,
                0,
                5,
                children=[
                    Note.air_crush_end(27370, 4, 4, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                27840,
                8,
                4,
                0,
                5,
                children=[
                    Note.air_crush_end(27850, 8, 4, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                28320,
                12,
                4,
                0,
                5,
                children=[
                    Note.air_crush_end(28330, 12, 4, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                28800,
                6,
                4,
                80,
                0,
                children=[
                    Note.air_crush_control(29520, 12, 4, 80, 0),
                    Note.air_crush_end(30240, 12, 4, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                28800,
                0,
                4,
                80,
                0,
                children=[
                    Note.air_crush_control(29520, 8, 4, 80, 0),
                    Note.air_crush_end(30240, 0, 4, 80, 0),
                ],
            ),
        ]
    )

    # BAR 5
    # Air crushes
    notes.extend(
        [
            Note.air_crush_begin(
                30720,
                0,
                4,
                80,
                240,
                children=[
                    Note.air_crush_control(31439, 6, 4, 80, 0),
                    Note.air_crush_end(32160, 0, 8, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                30720,
                6,
                4,
                80,
                240,
                children=[
                    Note.air_crush_control(31439, 12, 4, 80, 0),
                    Note.air_crush_end(32160, 12, 4, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                1,
                1,
                40,
                0,
                variation_id=1,
                children=[
                    Note.air_crush_end(34080, 1, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                2,
                1,
                40,
                0,
                variation_id=2,
                children=[
                    Note.air_crush_end(34080, 2, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                3,
                1,
                40,
                0,
                variation_id=3,
                children=[
                    Note.air_crush_end(34080, 3, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                4,
                1,
                40,
                0,
                variation_id=12,
                children=[
                    Note.air_crush_end(34080, 4, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                5,
                1,
                40,
                0,
                variation_id=4,
                children=[
                    Note.air_crush_end(34080, 5, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                6,
                1,
                40,
                0,
                variation_id=5,
                children=[
                    Note.air_crush_end(34080, 6, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                7,
                1,
                40,
                0,
                variation_id=13,
                children=[
                    Note.air_crush_end(34080, 7, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                8,
                1,
                40,
                0,
                variation_id=14,
                children=[
                    Note.air_crush_end(34080, 8, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                10,
                1,
                40,
                0,
                variation_id=7,
                children=[
                    Note.air_crush_end(34080, 10, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                12,
                1,
                40,
                0,
                variation_id=15,
                children=[
                    Note.air_crush_end(34080, 12, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                11,
                1,
                40,
                0,
                variation_id=8,
                children=[
                    Note.air_crush_end(34080, 11, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                9,
                1,
                40,
                0,
                variation_id=6,
                children=[
                    Note.air_crush_end(34080, 9, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                13,
                1,
                40,
                0,
                variation_id=10,
                children=[
                    Note.air_crush_end(34080, 13, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                32640,
                14,
                1,
                40,
                0,
                variation_id=11,
                children=[
                    Note.air_crush_end(34080, 14, 1, 40, 0),
                ],
            ),
            Note.air_crush_begin(
                34560,
                0,
                4,
                0,
                4,
                variation_id=35,
                children=[
                    Note.air_crush_end(34572, 8, 2, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                35040,
                12,
                4,
                0,
                4,
                variation_id=35,
                children=[
                    Note.air_crush_end(35052, 6, 2, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                35520,
                0,
                4,
                0,
                4,
                variation_id=35,
                children=[
                    Note.air_crush_end(35532, 8, 2, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                35520,
                12,
                4,
                80,
                4,
                variation_id=35,
                children=[
                    Note.air_crush_end(35532, 6, 2, 0, 0),
                ],
            ),
            Note.air_crush_begin(
                36000,
                0,
                4,
                80,
                4,
                variation_id=35,
                children=[
                    Note.air_crush_end(36012, 8, 2, 0, 0),
                ],
            ),
            Note.air_crush_begin(
                36000,
                12,
                4,
                0,
                4,
                variation_id=35,
                children=[
                    Note.air_crush_end(36012, 6, 2, 80, 0),
                ],
            ),
        ]
    )

    # Taps
    notes.append(
        Note.tap(
            36480,
            0,
            4,
            children=[
                Note.air(
                    36480,
                    0,
                    4,
                    direction=Direction.UP,
                    children=[
                        Note.air_hold_begin(
                            36480,
                            0,
                            4,
                            80,
                            children=[
                                Note.air_hold_end_noact(37920, 0, 4, 800),
                            ],
                        ),
                    ],
                ),
            ],
        )
    )

    # Air crushes
    notes.append(
        Note.air_crush_begin(
            36480,
            12,
            4,
            80,
            AirCrushOption.HEAD_ONLY,
            children=[
                Note.air_crush_end(37920, 12, 4, 80, 0),
            ],
        )
    )

    # Taps
    notes.append(
        Note.tap(
            36480,
            4,
            4,
            children=[
                Note.air(
                    36480,
                    4,
                    4,
                    direction=Direction.UP,
                    children=[
                        Note.air_slide_begin(
                            36480,
                            4,
                            4,
                            80,
                            children=[
                                Note.air_slide_step(36960, 4, 8, 80),
                                Note.air_slide_control(37440, 4, 8, 80),
                                Note.air_slide_end_noact(37920, 4, 4, 80),
                            ],
                        ),
                    ],
                ),
            ],
        )
    )

    # Air crushes
    notes.append(
        Note.air_crush_begin(
            36960,
            12,
            4,
            80,
            AirCrushOption.HEAD_ONLY,
            variation_id=35,
            children=[
                Note.air_crush_end(36961, 12, 4, 80, 0),
            ],
        )
    )

    # BAR 6
    # Air crushes
    notes.append(
        Note.air_crush_begin(
            38400,
            12,
            4,
            0,
            0,
            variation_id=3,
            children=[
                Note.air_crush_control(38401, 12, 4, 80, 0),
                Note.air_crush_end(39840, 0, 4, 80, 0),
            ],
        )
    )

    # Taps
    notes.extend(
        [
            Note.tap(
                38400,
                6,
                4,
                children=[
                    Note.air(
                        38400,
                        6,
                        4,
                        direction=Direction.UP,
                        children=[
                            Note.air_slide_begin(
                                38400,
                                6,
                                4,
                                80,
                                children=[
                                    Note.air_slide_end(39840, 12, 4, 80),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            Note.tap(
                38400,
                12,
                4,
                children=[
                    Note.air(
                        38400,
                        12,
                        4,
                        direction=Direction.UP,
                        children=[
                            Note.air_slide_begin(
                                38400,
                                12,
                                4,
                                80,
                                children=[
                                    Note.air_slide_end(39840, 0, 4, 80),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            Note.tap(
                38400,
                0,
                4,
                children=[
                    Note.air(
                        38400,
                        0,
                        4,
                        direction=Direction.UP,
                        children=[
                            Note.air_slide_begin(
                                38400,
                                0,
                                4,
                                80,
                                children=[
                                    Note.air_slide_end(39840, 6, 4, 80),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )

    # Air crushes
    notes.extend(
        [
            Note.air_crush_begin(
                38400,
                6,
                4,
                0,
                0,
                variation_id=6,
                children=[
                    Note.air_crush_control(38401, 6, 4, 80, 0),
                    Note.air_crush_end(39840, 12, 4, 80, 0),
                ],
            ),
            Note.air_crush_begin(
                38400,
                0,
                4,
                0,
                0,
                variation_id=5,
                children=[
                    Note.air_crush_control(38401, 0, 4, 80, 0),
                    Note.air_crush_end(39840, 6, 4, 80, 0),
                ],
            ),
        ]
    )

    # Damage notes
    notes.extend(
        [
            Note.damage(40320, 0, 4),
            Note.damage(40560, 4, 4),
            Note.damage(40800, 8, 4),
            Note.damage(41040, 12, 4),
            Note.damage(41280, 8, 4),
            Note.damage(41520, 4, 4),
            Note.damage(41760, 0, 4),
        ]
    )

    # Holds
    notes.append(
        Note.hold_begin(
            42240,
            0,
            4,
            children=[
                Note.hold_end(44156, 0, 4),
            ],
        )
    )

    # Damage notes
    notes.extend(
        [
            Note.damage(42720, 6, 4),
            Note.damage(42720, 6, 4),
            Note.damage(42840, 6, 4),
            Note.damage(42840, 6, 4),
            Note.damage(42960, 6, 4),
            Note.damage(42960, 6, 4),
            Note.damage(43080, 6, 4),
            Note.damage(43080, 6, 4),
            Note.damage(43200, 6, 4),
            Note.damage(43200, 6, 4),
            Note.damage(43320, 6, 4),
            Note.damage(43320, 6, 4),
            Note.damage(43440, 6, 4),
            Note.damage(43440, 6, 4),
            Note.damage(43560, 6, 4),
            Note.damage(43560, 6, 4),
            Note.damage(43680, 6, 4),
            Note.damage(43680, 6, 4),
        ]
    )

    # Holds
    notes.append(
        Note.hold_begin(
            44160,
            12,
            4,
            children=[
                Note.hold_end(46076, 12, 4),
            ],
        )
    )

    # Damage notes
    notes.extend(
        [
            Note.damage(44640, 6, 4),
            Note.damage(44640, 6, 4),
            Note.damage(44640, 6, 4),
            Note.damage(44700, 0, 4),
            Note.damage(44760, 6, 4),
            Note.damage(44760, 6, 4),
            Note.damage(44760, 6, 4),
            Note.damage(44820, 0, 4),
            Note.damage(44880, 6, 4),
            Note.damage(44880, 6, 4),
            Note.damage(44880, 6, 4),
            Note.damage(44940, 0, 4),
            Note.damage(45000, 6, 4),
            Note.damage(45000, 6, 4),
            Note.damage(45000, 6, 4),
            Note.damage(45060, 0, 4),
            Note.damage(45120, 6, 4),
            Note.damage(45120, 6, 4),
            Note.damage(45120, 6, 4),
            Note.damage(45180, 0, 4),
            Note.damage(45240, 6, 4),
            Note.damage(45240, 6, 4),
            Note.damage(45240, 6, 4),
            Note.damage(45300, 0, 4),
            Note.damage(45360, 6, 4),
            Note.damage(45360, 6, 4),
            Note.damage(45360, 6, 4),
            Note.damage(45420, 0, 4),
            Note.damage(45480, 6, 4),
            Note.damage(45480, 6, 4),
            Note.damage(45480, 6, 4),
            Note.damage(45540, 0, 4),
            Note.damage(45600, 6, 4),
            Note.damage(45600, 6, 4),
            Note.damage(45600, 6, 4),
            Note.damage(45660, 0, 4),
        ]
    )

    # BAR 7
    # Slides
    notes.append(
        Note.slide_begin(
            46080,
            0,
            4,
            children=[
                Note.slide_step(47040, 12, 4),
                Note.slide_end(47520, 0, 4),
            ],
        )
    )

    # Holds
    notes.extend(
        [
            Note.hold_begin(
                48000,
                6,
                4,
                children=[
                    Note.hold_end(49440, 6, 4, timeline_id=1),
                ],
            ),
            Note.hold_begin(
                48000,
                10,
                4,
                children=[
                    Note.hold_end(49440, 10, 4, timeline_id=3),
                ],
            ),
            Note.hold_begin(
                48000,
                2,
                4,
                children=[
                    Note.hold_end(49440, 2, 4, timeline_id=2),
                ],
            ),
        ]
    )

    return notes


def main() -> None:
    mg = Margrete("127.0.0.1:48731")
    print(mg.ping())

    with mg.open_append("official example") as tx:
        tx.chart.events.bpm.append(BpmEvent(tick=0, bpm=120.0))
        tx.chart.events.beat.append(
            BeatChangeEvent(bar=0, beats_per_bar=4, beat_unit=4)
        )
        tx.chart.events.til.append(
            TimelineSpeedEvent(tick=0, timeline_id=0, speed=1.0)
        )
        tx.chart.notes.extend(build_official_chart())


if __name__ == "__main__":
    main()
